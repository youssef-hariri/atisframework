# main.py (COMPLETE VERSION)
import os
import sys
import glob
import json
import shutil
from datetime import datetime
from pathlib import Path
from deepseek_client import DeepSeekClient
from keyword_manager import KeywordManager
from co_occurrence_analyzer import CoOccurrenceAnalyzer

def select_folder_console(prompt: str) -> str:
    """Select folder using console input"""
    print(f"\n{prompt}")
    print("Enter the full path to the folder (or drag and drop folder here):")
    folder_path = input("> ").strip()
    
    # Remove quotes if user drag-dropped
    folder_path = folder_path.strip("'\"")
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder does not exist: {folder_path}")
        return select_folder_console(prompt)
    
    return folder_path

def select_file_console(prompt: str, file_extension: str = ".csv") -> str:
    """Select file using console input"""
    print(f"\n{prompt}")
    print("Enter the full path to the file (or drag and drop file here):")
    file_path = input("> ").strip()
    
    # Remove quotes if user drag-dropped
    file_path = file_path.strip("'\"")
    
    if not os.path.exists(file_path):
        print(f"Error: File does not exist: {file_path}")
        return select_file_console(prompt, file_extension)
    
    if not file_path.lower().endswith(file_extension.lower()):
        print(f"Warning: File doesn't have {file_extension} extension")
        proceed = input("Continue anyway? (y/n): ").lower()
        if proceed != 'y':
            return select_file_console(prompt, file_extension)
    
    return file_path

def setup_directories(base_output_dir="output"):
    """Create directory structure for results"""
    # Create timestamp for unique output folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_output_dir, f"analysis_results_{timestamp}")
    results_dir = os.path.join(output_dir, "enriched_json_files")
    backup_dir = os.path.join(output_dir, "original_json_backup")
    
    # Create directories
    for directory in [output_dir, results_dir, backup_dir]:
        os.makedirs(directory, exist_ok=True)
    
    return output_dir, results_dir, backup_dir

def backup_and_enrich_json_files(json_files, backup_dir, results_dir):
    """Create backup copies and add ATIS pillar field"""
    enriched_files = []
    
    print(f"\nBacking up and enriching {len(json_files)} JSON files...")
    
    for json_file in json_files:
        try:
            # Read original file
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Create backup
            backup_path = os.path.join(backup_dir, os.path.basename(json_file))
            shutil.copy2(json_file, backup_path)
            
            # Enrich data with ATIS pillar field
            enriched_data = enrich_json_structure(data, json_file)
            
            # Save enriched version
            enriched_path = os.path.join(results_dir, os.path.basename(json_file))
            with open(enriched_path, 'w') as f:
                json.dump(enriched_data, f, indent=2)
            
            enriched_files.append(enriched_path)
            
            print(f"  ✓ {os.path.basename(json_file)}")
            
        except Exception as e:
            print(f"  ✗ {os.path.basename(json_file)}: {e}")
    
    print(f"\nBackup complete:")
    print(f"  Original files backed up to: {backup_dir}")
    print(f"  Enriched files saved to: {results_dir}")
    
    return enriched_files

def enrich_json_structure(data, filename):
    """Add ATIS pillar field to JSON structure"""
    
    def enrich_item(item):
        """Add ATIS pillar field to a single item"""
        if isinstance(item, dict):
            # Add atis_pillars field if not present
            if 'atis_pillars' not in item:
                item['atis_pillars'] = []
            # Add analysis metadata
            item['_analysis_metadata'] = {
                'source_file': os.path.basename(filename),
                'processed': False,
                'processed_timestamp': None
            }
        return item
    
    # Handle different JSON structures
    if isinstance(data, list):
        # List of items
        for i, item in enumerate(data):
            data[i] = enrich_item(item)
    elif isinstance(data, dict):
        # Single item
        data = enrich_item(data)
        # Check if it contains a list of quotes
        for key, value in data.items():
            if isinstance(value, list) and key in ['quotes', 'interview_segments', 'data']:
                for j, item in enumerate(value):
                    if isinstance(item, dict):
                        value[j] = enrich_item(item)
    
    return data

def update_json_with_results(json_file, pillar_data):
    """Update JSON file with ATIS pillar analysis results"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        updated = update_json_structure(data, pillar_data, json_file)
        
        with open(json_file, 'w') as f:
            json.dump(updated, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error updating {json_file}: {e}")
        return False

def update_json_structure(data, pillar_data, filename):
    """Update JSON structure with analysis results"""
    
    def update_item(item, quote, pillars):
        """Update a single item with pillars"""
        if isinstance(item, dict):
            item_expert_quote = item.get('expert_quote', item.get('quote', item.get('Expert Quote (Slang)', '')))
            
            # Check if this is the matching quote
            if item_expert_quote.strip() == quote.strip():
                item['atis_pillars'] = pillars
                if '_analysis_metadata' in item:
                    item['_analysis_metadata']['processed'] = True
                    item['_analysis_metadata']['processed_timestamp'] = datetime.now().isoformat()
        
        return item
    
    # Update based on data structure
    if isinstance(data, list):
        # List of items
        for i, item in enumerate(data):
            for quote, pillars in pillar_data.items():
                data[i] = update_item(item, quote, pillars)
    elif isinstance(data, dict):
        # Single item or nested structure
        for quote, pillars in pillar_data.items():
            data = update_item(data, quote, pillars)
        
        # Check for nested lists
        for key, value in data.items():
            if isinstance(value, list) and key in ['quotes', 'interview_segments', 'data']:
                for j, item in enumerate(value):
                    for quote, pillars in pillar_data.items():
                        if isinstance(item, dict):
                            value[j] = update_item(item, quote, pillars)
    
    return data

def main():
    # Check API key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        print("Set it with: export DEEPSEEK_API_KEY='your-key-here'")
        print("Or on Windows: set DEEPSEEK_API_KEY=your-key-here")
        sys.exit(1)
    
    print("="*60)
    print("ATIS FRAMEWORK CO-OCCURRENCE ANALYSIS")
    print("="*60)
    
    # Setup directories
    output_dir, results_dir, backup_dir = setup_directories()
    print(f"\nOutput will be saved to: {output_dir}")
    
    # Select JSON files folder
    print("\n" + "="*50)
    print("JSON FILES SELECTION")
    print("="*50)
    json_folder = select_folder_console("Select folder containing JSON files")
    
    # Find JSON files
    json_files = glob.glob(os.path.join(json_folder, "*.json"))
    if not json_files:
        print(f"\nNo JSON files found in {json_folder}")
        sys.exit(1)
    
    print(f"\nFound {len(json_files)} JSON files:")
    for i, file in enumerate(json_files[:10], 1):
        print(f"  {i}. {os.path.basename(file)}")
    if len(json_files) > 10:
        print(f"  ... and {len(json_files) - 10} more")
    
    # Backup and enrich JSON files
    enriched_files = backup_and_enrich_json_files(json_files, backup_dir, results_dir)
    
    # Select CSV file
    print("\n" + "="*50)
    print("CSV FILE SELECTION")
    print("="*50)
    
    csv_path = select_file_console("Select CSV file containing your data", ".csv")
    
    if not os.path.exists(csv_path):
        print(f"\nError: File not found: {csv_path}")
        sys.exit(1)
    
    print(f"\nSelected CSV file: {os.path.basename(csv_path)}")
    
    # Initialize clients
    print("\n" + "="*50)
    print("INITIALIZING ANALYSIS")
    print("="*50)
    
    print("Initializing DeepSeek client...")
    deepseek_client = DeepSeekClient()
    keyword_manager = KeywordManager(deepseek_client)
    
    # Build dynamic keyword dictionary
    if enriched_files:
        print(f"\nBuilding dynamic keyword dictionary from {len(enriched_files)} enriched JSON files...")
        sample_size = min(5, len(enriched_files))
        dynamic_dict = keyword_manager.build_from_json_files(enriched_files, sample_size=sample_size)
        print(f"\nExtracted keywords:")
        for pillar, keywords in dynamic_dict.items():
            print(f"  {pillar}: {len(keywords)} keywords (sample: {', '.join(keywords[:3])}...)")
        
        # Save keyword dictionary
        keyword_manager.save_keyword_dict(os.path.join(output_dir, "dynamic_keywords.json"))
    else:
        print("\nUsing base keyword dictionary.")
    
    # Initialize analyzer
    analyzer = CoOccurrenceAnalyzer(keyword_manager, deepseek_client)
    
    # Load and process CSV data
    print(f"\nLoading CSV data from {os.path.basename(csv_path)}...")
    try:
        df = analyzer.load_csv_data(csv_path)
        print(f"  ✓ Loaded {len(df)} quotes")
    except Exception as e:
        print(f"  ✗ Error loading CSV: {e}")
        sys.exit(1)
    
    # Process dataset
    print("\nProcessing quotes with hybrid approach...")
    try:
        results_df = analyzer.process_dataset(df)
        print(f"  ✓ Processed {len(results_df)} quotes")
    except Exception as e:
        print(f"  ✗ Error processing quotes: {e}")
        sys.exit(1)
    
    # Update JSON files with results
    print("\nUpdating JSON files with analysis results...")
    
    # Group results by quote for efficient updating
    quote_to_pillars = {}
    for _, row in results_df.iterrows():
        quote = row['quote']
        pillars = row['atis_pillars']
        quote_to_pillars[quote] = pillars
    
    # Update each enriched JSON file
    updated_count = 0
    for json_file in enriched_files:
        if update_json_with_results(json_file, quote_to_pillars):
            updated_count += 1
            print(f"  ✓ Updated {os.path.basename(json_file)}")
        else:
            print(f"  ✗ Failed to update {os.path.basename(json_file)}")
    
    print(f"\nUpdated {updated_count}/{len(enriched_files)} JSON files")
    
    # Run co-occurrence analysis
    print("\nCalculating co-occurrence...")
    try:
        co_occurrence_df = analyzer.calculate_co_occurrence()
        print(f"  ✓ Found {len(co_occurrence_df)} co-occurrence pairs")
    except Exception as e:
        print(f"  ✗ Error calculating co-occurrence: {e}")
        sys.exit(1)
    
    # Calculate statistics
    print("\nCalculating statistics...")
    try:
        stats = analyzer.calculate_statistics(co_occurrence_df)
        print(f"  ✓ Calculated statistics")
    except Exception as e:
        print(f"  ✗ Error calculating statistics: {e}")
        sys.exit(1)
    
    # Save results
    print("\nSaving analysis results...")
    try:
        # Save processed data
        results_df.to_csv(os.path.join(output_dir, "processed_quotes.csv"), index=False)
        
        # Save co-occurrence data
        co_occurrence_df.to_csv(os.path.join(output_dir, "co_occurrence_data.csv"), index=False)
        
        # Save statistics
        with open(os.path.join(output_dir, "statistics.json"), 'w') as f:
            json.dump(stats, f, indent=2)
        
        # Generate and save visualization data
        viz_data = analyzer.generate_visualization_data(stats)
        with open(os.path.join(output_dir, "visualization_data.json"), 'w') as f:
            json.dump(viz_data, f, indent=2)
        
        # Generate summary report
        summary = analyzer.generate_summary_report(stats, viz_data)
        with open(os.path.join(output_dir, "summary_report.md"), 'w') as f:
            f.write(summary)
        
        print(f"  ✓ Saved all results to {output_dir}")
        
    except Exception as e:
        print(f"  ✗ Error saving results: {e}")
        sys.exit(1)
    
    # Print final summary
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE - RESULTS SUMMARY")
    print("="*60)
    
    print(f"\n📁 OUTPUT DIRECTORY STRUCTURE:")
    print(f"   {output_dir}/")
    print(f"   ├── enriched_json_files/       # JSON files with ATIS pillars added")
    print(f"   ├── original_json_backup/      # Backup of original JSON files")
    print(f"   ├── processed_quotes.csv       # All quotes with analysis")
    print(f"   ├── co_occurrence_data.csv     # Co-occurrence pairs")
    print(f"   ├── statistics.json           # Statistical analysis")
    print(f"   ├── visualization_data.json   # Data for charts")
    print(f"   ├── summary_report.md         # Human-readable summary")
    if enriched_files:
        print(f"   └── dynamic_keywords.json     # Extracted keyword dictionary")
    
    print(f"\n📊 KEY FINDINGS:")
    print("-" * 40)
    
    # Show prevalence
    if 'stressor_prevalence' in stats:
        print("\nAI Stressor Prevalence:")
        for stressor, data in stats['stressor_prevalence'].items():
            stressor_name = stressor.replace('_', ' ').title()
            print(f"  {stressor_name}: {data['percentage']:.1f}%")
    
    # Show strongest links
    if 'strongest_links' in stats and stats['strongest_links']:
        print("\nTop 3 Strongest Stressor-Pillar Links:")
        for link in stats['strongest_links'][:3]:
            stressor_name = link['stressor'].replace('_', ' ').title()
            print(f"  {stressor_name} → {link['pillar']}: {link['strength']:.1f}%")
    
    # Show method usage
    if 'method_analysis' in stats:
        print(f"\n🛠️ METHOD USAGE:")
        print(f"  LLM Analysis: {stats['method_analysis']['llm_percentage']:.1f}% of quotes")
        print(f"  Keyword Matching: {100 - stats['method_analysis']['llm_percentage']:.1f}% of quotes")
    
    print(f"\n✅ All files have been saved. Check the '{output_dir}' directory for complete results.")

if __name__ == "__main__":
    main()
