"""Fine-tuning API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import logging

from src.data import schemas
from src.ai.finetuning_service import FineTuningService
from src.api.auth_routes import get_current_user
from src.workers.tasks import create_finetuning_job_task
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/finetuning",
    tags=["finetuning"],
)

# Initialize services
finetuning_service = FineTuningService()


@router.post(
    "/jobs",
    response_model=schemas.FineTuningJob,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new fine-tuning job",
)
async def create_finetuning_job(
    request: schemas.FineTuningJobCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new fine-tuning job.
    
    - **name**: Name for the fine-tuning job
    - **base_model**: Base model to fine-tune (gpt-3.5-turbo, gpt-4, etc.)
    - **training_data**: List of {prompt, completion} training examples
    - **validation_data**: Optional validation data
    - **epochs**: Number of training epochs (default: 3)
    """
    try:
        # Create fine-tuning job in database
        job_metadata = await finetuning_service.create_finetuning_job(
            name=request.name,
            model=request.base_model,
            training_data=request.training_data,
            validation_data=request.validation_data,
            hyperparameters={
                "epochs": request.epochs,
                "learning_rate_multiplier": request.learning_rate_multiplier,
                "batch_size": request.batch_size,
            },
            user_id=current_user.get("id"),
        )
        
        # Queue async job
        # TODO: Store job in database first, then queue task
        # create_finetuning_job_task.delay(job_id)
        
        return job_metadata
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating fine-tuning job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create fine-tuning job"
        )


@router.get(
    "/jobs/{job_id}",
    response_model=schemas.FineTuningJob,
    summary="Get fine-tuning job status",
)
async def get_finetuning_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get status and details of a fine-tuning job.
    
    - **job_id**: ID of the fine-tuning job
    """
    try:
        job = await finetuning_service.get_finetuning_job(job_id)
        
        # TODO: Check user authorization
        
        return job
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving fine-tuning job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fine-tuning job"
        )


@router.get(
    "/jobs",
    response_model=List[schemas.FineTuningJob],
    summary="List fine-tuning jobs",
)
async def list_finetuning_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """List fine-tuning jobs for the current user.
    
    - **status**: Filter by job status (pending, training, completed, failed, cancelled)
    - **limit**: Maximum number of jobs to return
    """
    try:
        jobs = await finetuning_service.list_finetuning_jobs(
            user_id=current_user.get("id"),
            status=status,
            limit=limit,
        )
        
        return jobs
        
    except Exception as e:
        logger.error(f"Error listing fine-tuning jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list fine-tuning jobs"
        )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=schemas.FineTuningJob,
    summary="Cancel a fine-tuning job",
)
async def cancel_finetuning_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Cancel an in-progress fine-tuning job.
    
    - **job_id**: ID of the job to cancel
    """
    try:
        job = await finetuning_service.cancel_finetuning_job(job_id)
        
        # TODO: Check user authorization
        
        return job
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling fine-tuning job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel fine-tuning job"
        )


@router.get(
    "/jobs/{job_id}/model",
    response_model=dict,
    summary="Get fine-tuned model name",
)
async def get_finetuned_model(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the fine-tuned model name after job completion.
    
    - **job_id**: ID of the completed fine-tuning job
    """
    try:
        model = await finetuning_service.get_finetuned_model(job_id)
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Fine-tuning job not completed yet"
            )
        
        return {"model": model}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving fine-tuned model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fine-tuned model"
        )


@router.post(
    "/prepare-data",
    response_model=List[schemas.TrainingData],
    summary="Prepare training data from queries",
)
async def prepare_training_data(
    queries: List[dict],
    format_template: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Prepare training data from existing query history.
    
    - **queries**: List of {question, answer} pairs
    - **format_template**: Optional template for formatting (e.g., "Q: {question}\\nA:")
    """
    try:
        training_data = await finetuning_service.prepare_training_data(
            queries=queries,
            format_template=format_template,
        )
        
        return training_data
        
    except Exception as e:
        logger.error(f"Error preparing training data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare training data"
        )


@router.get(
    "/jobs/{job_id}/evaluate",
    response_model=dict,
    summary="Evaluate fine-tuned model quality",
)
async def evaluate_finetuning_quality(
    job_id: str,
    validation_examples: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """Evaluate quality of a fine-tuned model.
    
    - **job_id**: ID of the fine-tuning job
    - **validation_examples**: Number of validation examples to use
    """
    try:
        # TODO: Fetch validation data from database
        validation_data = []
        
        metrics = await finetuning_service.evaluate_finetuning_quality(
            job_id=job_id,
            validation_data=validation_data,
        )
        
        return metrics
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error evaluating fine-tuning quality: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate fine-tuning quality"
        )
