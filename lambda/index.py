import json
import boto3
import os

s3 = boto3.client('s3')

BUCKET_NAME = os.environ['BUCKET_NAME']
FILE_KEY = os.environ['FILE_KEY']

def handler(event, context):
    try:
        # Get terminal ID from query parameters
        query_params = event.get('queryStringParameters', {})
        terminal_id = query_params.get('terminal')

        if not terminal_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing terminal query parameter'})
            }

        # Fetch JSON file from S3
        response = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_KEY)
        file_content = response['Body'].read().decode('utf-8')
        terminals = json.loads(file_content)

        # Filter for the terminal ID
        result = next((item for item in terminals if item['terminal'] == terminal_id), None)

        if result:
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Terminal not found'})
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error'})
        }
