"""
Inference script for batch processing BIS standard recommendations.

Usage:
    python inference.py --input input.json --output output.json

Input format (input.json):
    [
        {"id": "1", "query": "cement for construction"}
    ]

Output format (output.json):
    [
        {
            "id": "1",
            "retrieved_standards": ["IS 269", "IS 8112", "IS 12269"],
            "latency_seconds": 0.45
        }
    ]
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from retrieval import get_retriever
from llm import LLMRecommender

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_standard_codes(recommendations: List[Dict]) -> List[str]:
    """Extract standard codes from recommendations."""
    codes = []
    for rec in recommendations:
        code = rec.get('code', '').strip()
        if code and code.startswith('IS'):
            codes.append(code)
    return codes


def process_queries(input_file: str, output_file: str):
    """Process queries from input file and write results to output file."""
    
    # Validate input file
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    # Load queries
    try:
        with open(input_path, 'r') as f:
            queries = json.load(f)
        logger.info(f"Loaded {len(queries)} queries from {input_file}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in input file: {e}")
        sys.exit(1)
    
    # Initialize models
    logger.info("Initializing retriever and recommender...")
    try:
        retriever = get_retriever()
        recommender = LLMRecommender()
        logger.info("Models initialized")
    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
        sys.exit(1)
    
    # Process queries
    results = []
    total_latency = 0
    
    for idx, item in enumerate(queries):
        try:
            item_id = item.get('id', str(idx))
            query = item.get('query', '').strip()
            
            if not query:
                logger.warning(f"Skipping item {item_id}: empty query")
                results.append({
                    "id": item_id,
                    "retrieved_standards": [],
                    "latency_seconds": 0.0,
                    "error": "Empty query"
                })
                continue
            
            logger.info(f"Processing query {idx+1}/{len(queries)}: {query[:50]}...")
            
            start_time = time.time()
            
            # Hybrid search
            retrieved_results = retriever.hybrid_search(query, top_k=5)
            retrieved_chunks = [chunk[1] for _, chunk in retrieved_results]
            
            # Generate recommendations
            recommendations = recommender.generate_recommendations(query, retrieved_chunks)
            
            # Extract codes
            standards = extract_standard_codes(recommendations)
            
            latency = time.time() - start_time
            total_latency += latency
            
            results.append({
                "id": item_id,
                "retrieved_standards": standards,
                "latency_seconds": round(latency, 2)
            })
            
            logger.info(f"✓ Query {item_id}: {len(standards)} standards in {latency:.2f}s")
        
        except Exception as e:
            logger.error(f"Error processing query {item.get('id', idx)}: {e}")
            results.append({
                "id": item.get('id', idx),
                "retrieved_standards": [],
                "latency_seconds": 0.0,
                "error": str(e)
            })
    
    # Write results
    output_path = Path(output_file)
    try:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results written to {output_file}")
    except Exception as e:
        logger.error(f"Failed to write output file: {e}")
        sys.exit(1)
    
    # Print summary
    avg_latency = total_latency / len(queries) if queries else 0
    logger.info(f"\n=== Summary ===")
    logger.info(f"Processed: {len(queries)} queries")
    logger.info(f"Successful: {sum(1 for r in results if 'error' not in r)}")
    logger.info(f"Total latency: {total_latency:.2f}s")
    logger.info(f"Avg latency: {avg_latency:.2f}s")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='BIS Standards Batch Inference',
        epilog='Example: python inference.py --input queries.json --output results.json'
    )
    parser.add_argument('--input', required=True, help='Input JSON file path')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    
    args = parser.parse_args()
    
    process_queries(args.input, args.output)