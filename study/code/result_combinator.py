import os
import json
import csv
import re
from tkinter import filedialog, Tk

def extract_metadata(filename):
    """
    Extracts Expert ID and AI Specificity from the filename.
    Assumes format: 'ExpertID anonymized_specificity.json'
    """
    # Pattern to find the Expert ID (e.g., P23) at the start
    expert_id_match = re.match(r'^([A-Z0-9]+)', filename)
    expert_id = expert_id_match.group(1) if expert_id_match else "Unknown"
    
    # Pattern to find the specificity after the underscore
    # e.g., 'stochastic_uncertainty' from 'P23 anonymized_stochastic_uncertainty.json'
    spec_match = re.search(r'_(.+)\.json$', filename)
    specificity = spec_match.group(1) if spec_match else "Unknown"
    
    return expert_id, specificity

def main():
    # 1. Select the folder containing the JSON results
    root = Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Select Folder containing JSON Results")
    
    if not folder_path:
        print("No folder selected. Exiting.")
        return

    output_csv = os.path.join(folder_path, "master_qualitative_matrix.csv")
    
    # 2. Define the CSV headers
    headers = [
        "Expert ID",
        "AI Specificity",
        "Mapped ID (Indicator/Friction)",
        "Is Negative Case",
        "Expert Quote (Slang)",
        "Rationale"
    ]

    count = 0
    try:
        with open(output_csv, mode='w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()

            # 3. Iterate through all JSON files
            for filename in os.listdir(folder_path):
                if filename.endswith(".json"):
                    expert_id, specificity = extract_metadata(filename)
                    file_path = os.path.join(folder_path, filename)
                    
                    with open(file_path, 'r', encoding='utf-8') as jf:
                        try:
                            data = json.load(jf)
                            
                            # 4. Fill the CSV rows
                            for entry in data:
                                writer.writerow({
                                    "Expert ID": expert_id,
                                    "AI Specificity": specificity,
                                    "Mapped ID (Indicator/Friction)": entry.get("mapped_id", ""),
                                    "Is Negative Case": entry.get("is_negative_case", False),
                                    "Expert Quote (Slang)": entry.get("expert_quote", ""),
                                    "Rationale": entry.get("rationale", "")
                                })
                                count += 1
                        except json.JSONDecodeError:
                            print(f"Error skipping invalid JSON: {filename}")

        print(f"--- SUCCESS ---")
        print(f"Master Matrix created at: {output_csv}")
        print(f"Total entries processed: {count}")

    except Exception as e:
        print(f"An error occurred during aggregation: {e}")

if __name__ == "__main__":
    main()
