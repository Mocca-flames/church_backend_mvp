import json

def extract_kanana_phones(input_file, output_file):
    kanana_phones = []
    with open(input_file, 'r') as f:
        data = json.load(f)
        for entry in data:
            metadata_str = entry.get("metadata_")
            if metadata_str:
                try:
                    metadata = json.loads(metadata_str)
                    tags = metadata.get("tags", [])
                    if "majaneng" in tags:
                        kanana_phones.append(entry.get("phone"))
                except json.JSONDecodeError:
                    pass
    
    # Write as plain text instead of JSON
    with open(output_file, 'w') as f:
        f.write('')
        f.write(','.join(kanana_phones))
        f.write('')

if __name__ == "__main__":
    input_json_file = "phone_data.json"
    output_json_file = "majaneng_phone.txt"  # Changed extension to .txt
    extract_kanana_phones(input_json_file, output_json_file)