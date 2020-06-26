__author__ = "Bruce Pannaman"

import boto3
import botocore


class s3:
    def __init__(self):
        self.bucketName = "{Your s3 bucket name}"
        self.local_filepath = "/tmp/temp_storage"
        self.s3client = boto3.client('s3')
        s3resource = boto3.resource('s3')
        self.s3resource = s3resource.Bucket(self.bucketName)

    def upload_to_s3(self, card_id):
        """
        Uploads a card file to s3

        :param card_id: card_id to be updated
        :return: None
        """

        self.s3client.upload_file("%s/%s.json" % (self.local_filepath, card_id), self.bucketName,
                                  "staging_cards/%s.json" % card_id)

    def get_file(self, card_id):
        """
        Downloads a card_id from s3

        :param card_id:
        :return:
        """
        try:
            self.s3resource.download_file("staging_cards/%s.json" % card_id,
                                          "%s/%s.json" % (self.local_filepath, card_id))
            print("successfully downloaded %s.json" % card_id)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
                return False
            else:
                return False
