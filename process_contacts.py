import re

def process_contacts(file_path="contact_list.txt", batch_size=1000):
    """
    Reads a file containing comma-separated phone numbers, removes duplicates,
    and saves them into batches of a specified size.

    Args:
        file_path (str): The path to the input file containing phone numbers.
        batch_size (int): The maximum number of contacts per batch file.
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Use regex to find all phone numbers, handling potential whitespace
    # This regex assumes phone numbers start with '+' and contain digits and possibly '-'
    phone_numbers = re.findall(r'\+[\d-]+', content)

    # Remove duplicates using a set
    unique_phone_numbers = sorted(list(set(phone_numbers)))

    print(f"Total contacts found: {len(phone_numbers)}")
    print(f"Unique contacts found: {len(unique_phone_numbers)}")

    # Create batches
    for i in range(0, len(unique_phone_numbers), batch_size):
        batch = unique_phone_numbers[i:i + batch_size]
        batch_filename = f"contact_batch_{i // batch_size + 1}.txt"
        try:
            with open(batch_filename, 'w') as f:
                f.write(','.join(batch))
            print(f"Created batch file: {batch_filename} with {len(batch)} contacts.")
        except Exception as e:
            print(f"Error writing to file {batch_filename}: {e}")

if __name__ == "__main__":
    process_contacts()
