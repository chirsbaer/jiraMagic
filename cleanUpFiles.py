import os
import shutil
from datetime import datetime
import re

def delete_date_folders():
    # Define the regex pattern for folders named in "YYYY-MM-DD" format
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    # Iterate over all items in the current directory
    for item in os.listdir():
        if os.path.isdir(item) and date_pattern.match(item):
            # Remove the folder and all its contents
            shutil.rmtree(item)
            print(f"Removed folder: {item}")
            
def main():
    delete_date_folders()
    

if __name__ == "__main__":
    main()
