import os
from dotenv import load_dotenv
import httpx

from config import HEADER, BASEURL




def main():
    load_dotenv()  # Load environment variables from .env file

    pat = os.getenv("LH_PAT")
    if not pat:
        print("Error: LH_PAT environment variable not set.")
        return

    api_endpoint = "/v1/posts/get/"

    # Create a copy of the header and format the PAT into it
    request_headers = HEADER.copy()
    request_headers["Authorization"] = request_headers["Authorization"].format(PAT=pat)

    try:
        url = BASEURL + api_endpoint
        response = httpx.get(url=url, headers=request_headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print("API Call Successful:")
        # Process the response, e.g., print JSON data
        print(response.json())
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}")
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
