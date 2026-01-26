#!/usr/bin/env python3
"""Example: Using PyParrot programmatically."""

from pyparrot.config import PipelineConfig
from pyparrot.pipeline import Pipeline
from pyparrot.evaluator import Evaluator


def main():
    """Example usage of PyParrot."""
    
    # Create a pipeline configuration
    config = PipelineConfig(
        name="example-pipeline",
        speech={"model": "whisper", "sample_rate": 16000},
        llm={"model": "gpt-3.5-turbo", "temperature": 0.7},
        docker={"image_name": "pyparrot-example", "port": 8000},
    )
    
    print("Created pipeline configuration:")
    print(f"  Name: {config.name}")
    print(f"  Speech Model: {config.speech.model}")
    print(f"  LLM Model: {config.llm.model}")
    print()

    # Save configuration to file
    config.to_yaml("example_config.yaml")
    print("Saved configuration to example_config.yaml")
    print()

    # Create pipeline instance
    pipeline = Pipeline(config)

    # Generate Dockerfile
    dockerfile = pipeline.get_dockerfile()
    print("Generated Dockerfile:")
    print("-" * 50)
    print(dockerfile)
    print("-" * 50)
    print()

    # Note: Build, start, stop would require Docker to be installed
    # pipeline.build()
    # pipeline.start()
    # pipeline.stop()

    # Run evaluation
    evaluator = Evaluator(config.name)
    print("Running evaluation on example dataset...")
    result = evaluator.evaluate(
        "examples/eval_dataset.json",
        output_path="evaluation_results.json",
    )

    print(f"Evaluation complete!")
    print(f"  Total samples: {result.metrics.get('total_samples', 0)}")
    print(f"  Successful: {result.metrics.get('successful_samples', 0)}")
    print(f"  Results saved to evaluation_results.json")


if __name__ == "__main__":
    main()
