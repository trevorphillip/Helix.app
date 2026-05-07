import requests

BASE_URL = "http://127.0.0.1:8000"

def test_rna_tools_endpoint():
    url = f"{BASE_URL}/rna_tools"
    payload = {
        "dna": "ATGCGTACGTACGTAGGCTAGGCTAGGCTAGGCTAGGCTAG",
        "start": 0,
        "end": 18,
        "max_codons": 4,
    }

    resp = requests.post(url, json=payload)
    print("Status:", resp.status_code)
    print("Raw JSON:")
    print(resp.text)

    if resp.status_code == 200:
        data = resp.json()
        print("\nCodons:")
        for row in data.get("rows", []):
            print(
                f"- codon {row['codon_index']}: dna={row['dna_codon']}, "
                f"mrna={row['mrna_codon']}, aa={row['aa_one']}"
            )
    else:
        print("Error calling API")

if __name__ == "__main__":
    test_rna_tools_endpoint()
