import requests
import base64

def main():
    
    # This URL is used for sending messages
    my_uri = "https://api.bulksms.com/v1/messages"

    # Change these values to match your own account
    my_username = "juniorflamebet"
    my_password = "Mauricesitwala@12!"

    # The details of the message we want to send
    my_data = {
        "to": [ "+27817584591", "+27762122008" ],
        "body": "Hello World!",
        "encoding": "UNICODE",
        "longMessageMaxParts": "30",
    }

    # Encode credentials to Base64
    credentials = f"{my_username}:{my_password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

    # Headers for the request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }

    # Make the POST request
    try:
        response = requests.post(
            my_uri,
            json=my_data,
            headers=headers
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Print the response from the API
        print(response.text)
    except requests.exceptions.RequestException as ex:
        # Show the general message
        print("An error occurred: {}".format(ex))
        # Print the detail that comes with the error if available
        if ex.response is not None:
            print("Error details: {}".format(ex.response.text))

if __name__ == "__main__":
    main()
