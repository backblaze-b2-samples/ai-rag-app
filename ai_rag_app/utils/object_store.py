# MIT License
#
# Copyright (c) 2025 Backblaze, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Tuple
from urllib.parse import urlparse

from botocore.client import BaseClient


def parse_s3_uri(uri: str) -> Tuple[str, str]:
    """
    Accept S3 URI, return bucket and key
    """
    parsed = urlparse(uri, allow_fragments=False)
    if parsed.scheme != 's3':
        raise ValueError(f'{uri} is not an s3 URI')
    return parsed.netloc, parsed.path.removeprefix('/')


def delete_all(client: BaseClient, uri: str):
    """
    Delete all keys with the given prefix
    """
    bucket_name, path = parse_s3_uri(uri)
    paginator = client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=path)
    for page in page_iterator:
        # Helpfully, ListObjectsV2 returns pages of up to 1,000 results, and
        # DeleteObjects accepts up to 1,000 object identifiers
        delete_keys = {'Objects': [{'Key': obj['Key']} for obj in page['Contents']]}
        client.delete_objects(Bucket=bucket_name, Delete=delete_keys)


def location_has_objects(client: BaseClient, uri: str):
    """
    Returns true if there are any files with the given prefix
    """
    bucket_name, path = parse_s3_uri(uri)
    response = client.list_objects_v2(Bucket=bucket_name, Prefix=path, MaxKeys=1)
    return response['KeyCount'] > 0
