from botocore.client import BaseClient


def delete_all(client: BaseClient, bucket_name: str, prefix: str):
    """
    Delete all keys with the given prefix
    """
    paginator = client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    for page in page_iterator:
        # Helpfully, ListObjectsV2 returns pages of up to 1,000 results, and
        # DeleteObjects accepts up to 1,000 object identifiers
        delete_keys = {'Objects': [{'Key': obj['Key']} for obj in page['Contents']]}
        client.delete_objects(Bucket=bucket_name, Delete=delete_keys)


def prefix_has_objects(client: BaseClient, bucket_name: str, prefix: str):
    """
    Returns true if there are any files with the given prefix
    """
    response = client.list_objects_v2(Bucket=bucket_name, Prefix=prefix, MaxKeys=1)
    return response['KeyCount'] > 0
