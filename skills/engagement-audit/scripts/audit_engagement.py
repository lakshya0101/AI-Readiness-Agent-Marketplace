import sys
import json
from .evaluators import EngagementEvaluator
from .models import FindingEncoder

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            print("[]", end="")
            return
            
        payload = json.loads(input_data)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error parsing JSON input: {e}\n")
        sys.exit(1)
        
    url = payload.get("url", "")
    html = payload.get("html", "")
    entry_type = payload.get("entry_type", "landing")
    page_type = payload.get("inferred_page_type", "")
    
    evaluator = EngagementEvaluator(url, html, entry_type, page_type)
    findings = evaluator.evaluate()
    
    print(json.dumps(findings, cls=FindingEncoder, indent=2))

if __name__ == "__main__":
    main()
