import pandas as pd

def analyze_negative_cases(input_file, output_csv):
    # 1. Load the automated results
    df = pd.read_csv(input_file)
    
    # 2. Isolate only Negative Cases (where expert says 'No Friction')
    # Ensuring we handle different boolean formats
    neg_cases = df[df['is_negative_case'].astype(str).str.upper() == 'TRUE'].copy()
    
    # 3. Aggregate metrics: Where is the theory being challenged?
    summary = neg_cases.groupby(['ai_specificity', 'mapped_id_(indicator/friction)']).size().reset_index(name='Frequency')
    summary = summary.sort_values(by=['ai_specificity', 'Frequency'], ascending=[True, False])
    
    # 4. Extract 'Why' - The first rationale for each group gives the qualitative 'reason'
    reasons = neg_cases.groupby(['ai_specificity', 'mapped_id_(indicator/friction)'])['rationale'].first().reset_index()
    
    # 5. Merge and Save
    final_report = pd.merge(summary, reasons, on=['ai_specificity', 'mapped_id_(indicator/friction)'])
    final_report.to_csv(output_csv, index=False)
    
    print(f"Negative Case Analysis Complete. Saved to: {output_csv}")
    print(f"Analyzed {len(neg_cases)} contradictions across {len(summary)} indicators.")

# Run the analysis
analyze_negative_cases('processed_quotes.csv', 'negative_case_summary.csv')
