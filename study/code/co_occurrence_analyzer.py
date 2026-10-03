# co_occurrence_analyzer.py
import pandas as pd
import numpy as np
import json
import re
import os
from typing import Dict, List, Tuple, Any
from collections import defaultdict
from datetime import datetime
from deepseek_client import DeepSeekClient
from keyword_manager import KeywordManager
from config import *

class CoOccurrenceAnalyzer:
    def __init__(self, keyword_manager: KeywordManager, deepseek_client: DeepSeekClient):
        self.keyword_manager = keyword_manager
        self.deepseek_client = deepseek_client
        self.results_df = None
        
    def load_csv_data(self, csv_path: str) -> pd.DataFrame:
        """Load and preprocess CSV data"""
        df = pd.read_csv(csv_path)
        
        # Ensure required columns exist
        required_columns = ['Expert ID', 'AI Specificity', 'Expert Quote (Slang)']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Clean data
        df = df.dropna(subset=['Expert Quote (Slang)'])
        df['Expert Quote (Slang)'] = df['Expert Quote (Slang)'].astype(str).str.strip()
        
        # Filter out very short quotes
        df = df[df['Expert Quote (Slang)'].str.len() > 10]
        
        return df
    
    def hybrid_pillar_detection(self, quote: str, quote_length: int,
                               total_processed: int) -> Tuple[List[str], str]:
        """
        Hybrid detection: keyword matching + LLM fallback
        Returns: (list_of_pillars, method_used)
        """
        # Decision logic for using LLM
        use_llm = (
            quote_length > 100 or  # Long/complex quotes
            quote_length < 20 or   # Very short/ambiguous
            "?" in quote or        # Contains questions
            total_processed % 3 == 0 or  # Every 3rd for diversity
            len(re.findall(r'\b(why|how|what|when|where)\b', quote.lower())) > 0
        )
        
        if use_llm:
            pillars = self.deepseek_client.extract_atis_pillars(quote)
            method = "LLM"
        else:
            pillars = self.keyword_manager.detect_pillars_keyword(quote)
            method = "Keyword"
        
        return pillars, method
    
    def process_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process entire dataset with hybrid approach"""
        results = []
        total_quotes = len(df)
        llm_count = 0
        
        print(f"Processing {total_quotes} quotes...")
        
        for idx, row in df.iterrows():
            quote = row['Expert Quote (Slang)']
            quote_length = len(quote.split())
            
            # Progress indicator
            if idx % 10 == 0:
                print(f"  Processed {idx}/{total_quotes} quotes...")
            
            # Detect ATIS pillars
            pillars, method = self.hybrid_pillar_detection(
                quote, quote_length, idx
            )
            
            if method == "LLM":
                llm_count += 1
            
            result = {
                'expert_id': row['Expert ID'],
                'ai_specificity': row['AI Specificity'],
                'quote': quote,
                'atis_pillars': pillars,
                'detection_method': method,
                'quote_length': quote_length,
                'original_index': idx
            }
            
            # Add optional columns if they exist
            for col in ['Mapped ID (Indicator/Friction)', 'Is Negative Case', 'Rationale']:
                if col in row:
                    result[col.lower().replace(' ', '_')] = row[col]
            
            results.append(result)
        
        # Create results DataFrame
        self.results_df = pd.DataFrame(results)
        
        print(f"\nProcessing complete:")
        print(f"  Total quotes: {total_quotes}")
        print(f"  LLM analyses: {llm_count} ({(llm_count/total_quotes)*100:.1f}%)")
        print(f"  Keyword analyses: {total_quotes - llm_count}")
        
        return self.results_df
    
    def calculate_context_window(self, expert_id: str, current_idx: int,
                                df_slice: pd.DataFrame, window_size: int = 2) -> pd.DataFrame:
        """Get quotes in context window for a specific expert"""
        # Filter to this expert's quotes
        expert_df = df_slice[df_slice['expert_id'] == expert_id].copy()
        expert_df = expert_df.sort_values('original_index').reset_index(drop=True)
        
        # Find position in expert's quotes
        try:
            pos = expert_df[expert_df['original_index'] == current_idx].index[0]
            start = max(0, pos - window_size)
            end = min(len(expert_df), pos + window_size + 1)
            return expert_df.iloc[start:end]
        except IndexError:
            return pd.DataFrame()
    
    def calculate_co_occurrence(self, window_size: int = 2) -> pd.DataFrame:
        """Calculate co-occurrence between AI stressors and ATIS pillars"""
        if self.results_df is None:
            raise ValueError("Run process_dataset() first")
        
        co_occurrences = []
        
        # Group by expert for context analysis
        experts = self.results_df['expert_id'].unique()
        
        for expert in experts:
            expert_quotes = self.results_df[self.results_df['expert_id'] == expert]
            
            for idx, row in expert_quotes.iterrows():
                stressor = row['ai_specificity']
                pillars_in_quote = row['atis_pillars']
                
                # 1. Direct co-occurrence (same quote)
                for pillar in pillars_in_quote:
                    co_occurrences.append({
                        'expert_id': expert,
                        'stressor': stressor,
                        'pillar': pillar,
                        'co_occurrence_type': 'direct',
                        'distance': 0,
                        'quote_context': 'same_quote'
                    })
                
                # 2. Contextual co-occurrence (nearby quotes)
                context = self.calculate_context_window(
                    expert, row['original_index'], self.results_df, window_size
                )
                
                for _, context_row in context.iterrows():
                    if context_row['original_index'] == row['original_index']:
                        continue  # Skip self
                    
                    distance = abs(context_row['original_index'] - row['original_index'])
                    context_pillars = context_row['atis_pillars']
                    
                    for pillar in context_pillars:
                        co_occurrences.append({
                            'expert_id': expert,
                            'stressor': stressor,
                            'pillar': pillar,
                            'co_occurrence_type': 'contextual',
                            'distance': distance,
                            'quote_context': f'within_{window_size}'
                        })
        
        return pd.DataFrame(co_occurrences)
    
    def calculate_statistics(self, co_occurrence_df: pd.DataFrame) -> Dict:
        """Calculate all statistics"""
        stats = {}
        
        # 1. Prevalence of AI stressors
        stressor_counts = self.results_df['ai_specificity'].value_counts()
        stats['stressor_prevalence'] = {
            str(stressor): {  # Convert to string for JSON serialization
                'count': int(count),  # Convert to int
                'percentage': float((count / len(self.results_df)) * 100)
            }
            for stressor, count in stressor_counts.items()
        }
        
        # 2. ATIS pillar frequency
        all_pillars = []
        for pillars in self.results_df['atis_pillars']:
            all_pillars.extend(pillars)
        
        pillar_counts = pd.Series(all_pillars).value_counts()
        stats['pillar_frequency'] = {
            str(k): int(v) for k, v in pillar_counts.to_dict().items()  # Convert to int
        }
        
        # 3. Co-occurrence matrix
        stressors = self.results_df['ai_specificity'].unique()
        pillars_list = ['Act', 'Train', 'Inquire', 'Standardize']
        
        matrix = {}
        for stressor in stressors:
            matrix[str(stressor)] = {}  # Convert to string
            stressor_quotes = self.results_df[self.results_df['ai_specificity'] == stressor]
            total_stressor = len(stressor_quotes)
            
            for pillar in pillars_list:
                # Count direct co-occurrences
                direct_count = len(co_occurrence_df[
                    (co_occurrence_df['stressor'] == stressor) &
                    (co_occurrence_df['pillar'] == pillar) &
                    (co_occurrence_df['co_occurrence_type'] == 'direct')
                ])
                
                # Count contextual co-occurrences
                context_count = len(co_occurrence_df[
                    (co_occurrence_df['stressor'] == stressor) &
                    (co_occurrence_df['pillar'] == pillar) &
                    (co_occurrence_df['co_occurrence_type'] == 'contextual')
                ])
                
                total_count = direct_count + context_count
                
                if total_stressor > 0:
                    percentage = float((total_count / total_stressor) * 100)
                else:
                    percentage = 0.0
                
                matrix[str(stressor)][pillar] = {
                    'direct_count': int(direct_count),
                    'context_count': int(context_count),
                    'total_count': int(total_count),
                    'percentage': float(round(percentage, 2))  # Convert to float
                }
        
        stats['co_occurrence_matrix'] = matrix
        
        # 4. Strongest links
        all_links = []
        for stressor, pillar_data in matrix.items():
            for pillar, link_data in pillar_data.items():
                all_links.append({
                    'stressor': str(stressor),
                    'pillar': str(pillar),
                    'strength': float(link_data['percentage']),  # Convert to float
                    'total_count': int(link_data['total_count'])
                })
        
        all_links.sort(key=lambda x: x['strength'], reverse=True)
        stats['strongest_links'] = all_links[:10]
        
        # 5. Method effectiveness
        method_stats = self.results_df['detection_method'].value_counts()
        stats['method_analysis'] = {
            'total_quotes': int(len(self.results_df)),
            'llm_quotes': int(method_stats.get('LLM', 0)),
            'keyword_quotes': int(method_stats.get('Keyword', 0)),
            'llm_percentage': float((method_stats.get('LLM', 0) / len(self.results_df)) * 100)
        }
        
        return stats
    
    def generate_visualization_data(self, stats: Dict) -> Dict:
        """Prepare data for visualization"""
        viz_data = {
            'heatmap_data': [],
            'prevalence_chart': [],
            'method_chart': [],
            'top_links': stats['strongest_links'][:5]
        }
        
        # Heatmap data
        matrix = stats['co_occurrence_matrix']
        for stressor, pillars in matrix.items():
            for pillar, data in pillars.items():
                viz_data['heatmap_data'].append({
                    'stressor': stressor.replace('_', ' ').title(),
                    'pillar': pillar,
                    'strength': data['percentage']
                })
        
        # Prevalence chart
        for stressor, data in stats['stressor_prevalence'].items():
            viz_data['prevalence_chart'].append({
                'stressor': stressor.replace('_', ' ').title(),
                'percentage': data['percentage']
            })
        
        # Method chart
        viz_data['method_chart'] = [
            {'method': 'LLM Analysis', 'count': stats['method_analysis']['llm_quotes']},
            {'method': 'Keyword Matching', 'count': stats['method_analysis']['keyword_quotes']}
        ]
        
        return viz_data
    
    def save_results(self, output_dir: str):
        """Save all results to files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Save processed data
        self.results_df.to_csv(f"{output_dir}/processed_quotes.csv", index=False)
        
        # Calculate and save co-occurrence
        co_occurrence_df = self.calculate_co_occurrence()
        co_occurrence_df.to_csv(f"{output_dir}/co_occurrence_data.csv", index=False)
        
        # Calculate and save statistics
        stats = self.calculate_statistics(co_occurrence_df)
        with open(f"{output_dir}/statistics.json", 'w') as f:
            json.dump(stats, f, indent=2)
        
        # Save visualization data
        viz_data = self.generate_visualization_data(stats)
        with open(f"{output_dir}/visualization_data.json", 'w') as f:
            json.dump(viz_data, f, indent=2)
        
        # Generate summary report
        summary = self.generate_summary_report(stats, viz_data)
        with open(f"{output_dir}/summary_report.md", 'w') as f:
            f.write(summary)
        
        print(f"\nResults saved to {output_dir}/")
        
    def generate_summary_report(self, stats: Dict, viz_data: Dict) -> str:
        """Generate markdown summary report"""
        report = f"""# ATIS Framework Co-occurrence Analysis Report

## Summary
- Total quotes analyzed: {len(self.results_df)}
- AI stressors identified: {len(stats['stressor_prevalence'])}
- Co-occurrence pairs found: {sum(len(v) for v in stats['co_occurrence_matrix'].values())}

## Prevalence of AI Stressors
"""
        for stressor, data in stats['stressor_prevalence'].items():
            report += f"- **{stressor.replace('_', ' ').title()}**: {data['percentage']:.1f}% of quotes\n"

        report += "\n## Top 5 Strongest Stressor-Pillar Links\n"
        for link in viz_data['top_links']:
            report += f"- **{link['stressor'].replace('_', ' ').title()} → {link['pillar']}**: {link['strength']:.1f}% ({link['total_count']} occurrences)\n"

        report += f"\n## Method Effectiveness\n"
        report += f"- LLM Analysis: {stats['method_analysis']['llm_percentage']:.1f}% of quotes\n"
        report += f"- Keyword Matching: {100 - stats['method_analysis']['llm_percentage']:.1f}% of quotes\n"

        return report
    
    def save_json_updates(self, results_df: pd.DataFrame, json_files: List[str]):
        """Update JSON files with analysis results"""
        print(f"\nUpdating {len(json_files)} JSON files with ATIS pillar results...")
        
        # Group quotes by JSON file (assuming filename contains participant ID)
        updates_by_file = defaultdict(list)
        
        for _, row in results_df.iterrows():
            expert_id = row['expert_id']
            quote = row['quote']
            pillars = row['atis_pillars']
            
            # Find matching JSON file
            for json_file in json_files:
                if expert_id in os.path.basename(json_file):
                    updates_by_file[json_file].append((quote, pillars))
                    break
        
        # Update each file
        for json_file, updates in updates_by_file.items():
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Update the data
                updated_data = self._update_json_data(data, updates)
                
                # Save back
                with open(json_file, 'w') as f:
                    json.dump(updated_data, f, indent=2)
                
                print(f"  ✓ Updated {os.path.basename(json_file)}")
                
            except Exception as e:
                print(f"  ✗ Error updating {os.path.basename(json_file)}: {e}")
        
        print(f"\nUpdated {len(updates_by_file)}/{len(json_files)} JSON files")
    
    def _update_json_data(self, data: Any, updates: List[Tuple[str, List[str]]]) -> Any:
        """Recursively update JSON data with ATIS pillars"""
        quote_to_pillars = {quote: pillars for quote, pillars in updates}
        
        def update_item(item: Any) -> Any:
            if isinstance(item, dict):
                # Check if this item has a quote
                quote = item.get('expert_quote', item.get('quote', item.get('Expert Quote (Slang)', '')))
                if quote and quote in quote_to_pillars:
                    item['atis_pillars'] = quote_to_pillars[quote]
                    # Mark as processed
                    if '_analysis_metadata' in item:
                        item['_analysis_metadata']['processed'] = True
                        item['_analysis_metadata']['processed_timestamp'] = datetime.now().isoformat()
                
                # Recursively update nested structures
                for key, value in item.items():
                    if isinstance(value, (list, dict)):
                        item[key] = update_structure(value)
            
            return item
        
        def update_structure(structure: Any) -> Any:
            if isinstance(structure, list):
                return [update_item(item) if isinstance(item, dict) else item for item in structure]
            elif isinstance(structure, dict):
                return update_item(structure)
            return structure
        
        return update_structure(data)
