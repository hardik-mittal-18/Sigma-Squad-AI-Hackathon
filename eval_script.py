"""
Evaluation script for BIS Standards Recommendation Engine.
Computes Hit@K, MRR@K, and latency metrics.

Usage:
    python eval_script.py --predictions predictions.json --ground_truth ground_truth.json
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluation metrics for ranking systems."""
    
    @staticmethod
    def hit_at_k(predicted: List[str], ground_truth: List[str], k: int = 3) -> int:
        """
        Hit@K: Whether any predicted item is in ground truth within top K.
        Returns 1 if hit, 0 otherwise.
        """
        top_k_predicted = predicted[:k]
        for item in top_k_predicted:
            if item in ground_truth:
                return 1
        return 0
    
    @staticmethod
    def mrr_at_k(predicted: List[str], ground_truth: List[str], k: int = 5) -> float:
        """
        MRR@K: Mean Reciprocal Rank - average of 1/rank of first correct item.
        """
        top_k_predicted = predicted[:k]
        for rank, item in enumerate(top_k_predicted, 1):
            if item in ground_truth:
                return 1.0 / rank
        return 0.0
    
    @staticmethod
    def ndcg_at_k(predicted: List[str], ground_truth: List[str], k: int = 5) -> float:
        """
        NDCG@K: Normalized Discounted Cumulative Gain.
        """
        # DCG calculation
        dcg = 0.0
        for rank, item in enumerate(predicted[:k], 1):
            if item in ground_truth:
                dcg += 1.0 / (1.0 + np.log2(rank))
        
        # IDCG calculation (ideal ranking)
        idcg = 0.0
        for rank in range(1, min(len(ground_truth) + 1, k + 1)):
            idcg += 1.0 / (1.0 + np.log2(rank))
        
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def precision_at_k(predicted: List[str], ground_truth: List[str], k: int = 5) -> float:
        """
        Precision@K: Fraction of top K items that are in ground truth.
        """
        top_k = predicted[:k]
        matches = sum(1 for item in top_k if item in ground_truth)
        return matches / k if k > 0 else 0.0
    
    @staticmethod
    def recall_at_k(predicted: List[str], ground_truth: List[str], k: int = 5) -> float:
        """
        Recall@K: Fraction of ground truth items found in top K.
        """
        top_k = predicted[:k]
        matches = sum(1 for item in top_k if item in ground_truth)
        return matches / len(ground_truth) if len(ground_truth) > 0 else 0.0


def load_json(file_path: str) -> List[Dict]:
    """Load JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def evaluate(predictions: List[Dict], ground_truth: List[Dict]) -> Dict:
    """
    Evaluate predictions against ground truth.
    
    Args:
        predictions: List of {"id": str, "retrieved_standards": [str]}
        ground_truth: List of {"id": str, "relevant_standards": [str]}
    
    Returns:
        Evaluation metrics dictionary
    """
    evaluator = Evaluator()
    
    # Create mapping for ground truth by ID
    gt_map = {item['id']: item.get('relevant_standards', []) for item in ground_truth}
    
    # Compute metrics
    hit_at_3_values = []
    hit_at_5_values = []
    mrr_at_5_values = []
    precision_at_3_values = []
    recall_at_3_values = []
    latencies = []
    
    for pred in predictions:
        item_id = pred['id']
        predicted_standards = pred.get('retrieved_standards', [])
        ground_truth_standards = gt_map.get(item_id, [])
        
        if not ground_truth_standards:
            logger.warning(f"No ground truth for ID {item_id}")
            continue
        
        # Compute metrics
        hit_3 = evaluator.hit_at_k(predicted_standards, ground_truth_standards, k=3)
        hit_5 = evaluator.hit_at_k(predicted_standards, ground_truth_standards, k=5)
        mrr = evaluator.mrr_at_k(predicted_standards, ground_truth_standards, k=5)
        prec_3 = evaluator.precision_at_k(predicted_standards, ground_truth_standards, k=3)
        rec_3 = evaluator.recall_at_k(predicted_standards, ground_truth_standards, k=3)
        
        hit_at_3_values.append(hit_3)
        hit_at_5_values.append(hit_5)
        mrr_at_5_values.append(mrr)
        precision_at_3_values.append(prec_3)
        recall_at_3_values.append(rec_3)
        
        if 'latency_seconds' in pred:
            latencies.append(pred['latency_seconds'])
    
    # Compute aggregates
    metrics = {
        'hit_at_3': statistics.mean(hit_at_3_values) if hit_at_3_values else 0.0,
        'hit_at_5': statistics.mean(hit_at_5_values) if hit_at_5_values else 0.0,
        'mrr_at_5': statistics.mean(mrr_at_5_values) if mrr_at_5_values else 0.0,
        'precision_at_3': statistics.mean(precision_at_3_values) if precision_at_3_values else 0.0,
        'recall_at_3': statistics.mean(recall_at_3_values) if recall_at_3_values else 0.0,
        'avg_latency_seconds': statistics.mean(latencies) if latencies else 0.0,
        'num_queries': len(hit_at_3_values)
    }
    
    return metrics


def print_metrics(metrics: Dict):
    """Print evaluation metrics."""
    print("\n" + "="*50)
    print("EVALUATION METRICS")
    print("="*50)
    print(f"Number of queries: {metrics['num_queries']}")
    print(f"Hit@3: {metrics['hit_at_3']:.4f}")
    print(f"Hit@5: {metrics['hit_at_5']:.4f}")
    print(f"MRR@5: {metrics['mrr_at_5']:.4f}")
    print(f"Precision@3: {metrics['precision_at_3']:.4f}")
    print(f"Recall@3: {metrics['recall_at_3']:.4f}")
    print(f"Avg Latency: {metrics['avg_latency_seconds']:.2f}s")
    print("="*50 + "\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluation Script')
    parser.add_argument('--predictions', required=True, help='Predictions JSON file')
    parser.add_argument('--ground_truth', required=True, help='Ground truth JSON file')
    parser.add_argument('--output', help='Output metrics JSON file (optional)')
    
    args = parser.parse_args()
    
    # Load data
    predictions = load_json(args.predictions)
    ground_truth = load_json(args.ground_truth)
    
    # Evaluate
    metrics = evaluate(predictions, ground_truth)
    
    # Print results
    print_metrics(metrics)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Metrics saved to {args.output}")
