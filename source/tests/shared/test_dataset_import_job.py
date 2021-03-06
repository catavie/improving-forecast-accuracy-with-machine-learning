# #####################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
#                                                                                                                     #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance     #
#  with the License. A copy of the License is located at                                                              #
#                                                                                                                     #
#  http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                     #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES  #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions     #
#  and limitations under the License.                                                                                 #
# #####################################################################################################################

from datetime import datetime

import boto3
import pytest
from botocore.stub import Stubber
from moto import mock_sts

from shared.Dataset.dataset_file import DatasetFile
from shared.config import Config
from shared.status import Status


@pytest.fixture
def forecast_stub():
    client = boto3.client("forecast", region_name="us-east-1")
    with Stubber(client) as stubber:
        yield stubber


@mock_sts
def test_dataset_import_job_status_lifecycle(configuration_data, forecast_stub, mocker):
    config = Config()
    config.config = configuration_data

    dataset_file = DatasetFile("RetailDemandTRM.csv", "some_bucket")
    dataset_import_job = config.dataset_import_job(dataset_file)
    size = 40

    # first call - doesn't exist
    forecast_stub.add_response("list_dataset_import_jobs", {"DatasetImportJobs": []})
    forecast_stub.add_response(
        "list_dataset_import_jobs",
        {
            "DatasetImportJobs": [
                {
                    "LastModificationTime": datetime(2015, 1, 1),
                    "DatasetImportJobArn": "arn:2015-1-1",
                },
                {
                    "LastModificationTime": datetime(2017, 1, 1),
                    "DatasetImportJobArn": "arn:2017-1-1",
                },
                {
                    "LastModificationTime": datetime(2016, 1, 1),
                    "DatasetImportJobArn": "arn:2016-1-1",
                },
            ]
        },
    )
    forecast_stub.add_response(
        "describe_dataset_import_job",
        {"Status": "ACTIVE", "FieldStatistics": {"item_id": {"Count": size}}},
    )
    forecast_stub.add_response(
        "list_dataset_import_jobs",
        {
            "DatasetImportJobs": [
                {
                    "LastModificationTime": datetime(2015, 1, 1),
                    "DatasetImportJobArn": "arn:2015-1-1",
                },
                {
                    "LastModificationTime": datetime(2017, 1, 1),
                    "DatasetImportJobArn": "arn:2017-1-1",
                },
                {
                    "LastModificationTime": datetime(2016, 1, 1),
                    "DatasetImportJobArn": "arn:2016-1-1",
                },
            ]
        },
    )
    forecast_stub.add_response(
        "describe_dataset_import_job",
        {"Status": "ACTIVE", "FieldStatistics": {"item_id": {"Count": size + 1}}},
    )

    dataset_import_job.cli = forecast_stub.client
    mocker.patch(
        "shared.Dataset.dataset_file.DatasetFile.size",
        new_callable=mocker.PropertyMock,
        return_value=size,
    )

    assert dataset_import_job.status == Status.DOES_NOT_EXIST

    # simulate finding an active dataset
    assert dataset_import_job.status == Status.ACTIVE

    # simulate a new dataset (with more lines) uploaded
    assert dataset_import_job.status == Status.DOES_NOT_EXIST


@mock_sts
def test_dataset_import_job_arn(configuration_data, forecast_stub, mocker):
    config = Config()
    config.config = configuration_data

    dataset_file = DatasetFile("RetailDemandTRM.csv", "some_bucket")
    dataset_import_job = config.dataset_import_job(dataset_file)

    # create some job history
    forecast_stub.add_response(
        "list_dataset_import_jobs",
        {
            "DatasetImportJobs": [
                {
                    "LastModificationTime": datetime(2015, 1, 1),
                    "DatasetImportJobArn": "arn:2015-1-1",
                },
                {
                    "LastModificationTime": datetime(2017, 1, 1),
                    "DatasetImportJobArn": "arn:aws:forecast:abcdefghijkl:us-east-1:dataset-import-job/RetailDemandTRM/RetailDemandTRM_2017_01_01_00_00_00",
                },
                {
                    "LastModificationTime": datetime(2016, 1, 1),
                    "DatasetImportJobArn": "arn:2016-1-1",
                },
            ]
        },
    )

    dataset_import_job.cli = forecast_stub.client
    assert (
        dataset_import_job.arn
        == f"arn:aws:forecast:abcdefghijkl:us-east-1:dataset-import-job/RetailDemandTRM/RetailDemandTRM_2017_01_01_00_00_00"
    )
