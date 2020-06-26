__author__ = "Bruce Pannaman"

import json
import configparser


class TestConditions:
    def __init__(self, input, schema, headers):
        self.input = input
        self.schema_location = "flask_app/schemas"
        self.headers = headers

        config = configparser.ConfigParser()
        config.read('flask_app/creds.ini')

        self.railsbank_api_key = config.get("Railsbank", "api_key")
        self.schema = self.read_schema(schema)

    def read_schema(self, schema):
        """
        Reads the schema JSON from files in Schema folder

        :return: JSON Object
        """
        with open("%s/%s" % (self.schema_location, schema), "r") as filo:
            return json.load(filo)

    def check_authentication(self):
        """
        Checks that the authorisation header is what is needed

        :return: success<bool> error message <str>
        """
        auth = self.headers.get("Authorization")
        if auth is None:
            return False, "Authorisation header needed"
        elif str(auth).replace("API-Key ", "") != self.railsbank_api_key:
            return False, "Unauthorised"
        else:
            return True, ""

    def data_type_checks(self):
        """
        Checks that the input of the request is of the right data type based on the schema of the

        Example Schema:

        {
            "field1": {
                "required": True,
                "data_type": "str"
            },
            "field2--nestedfield1": {
                "required": False,
                "data_type": ["bool", "None"]
            },
            "field3": {
                "required": False,
                "data_type": ["enum", "None"],
                "options": ["charge", "refund"]
            }
        }

        :param schema: Schema object
        :param input: The request of the call
        :return: success <boolean>, Error <str, None>
        """

        success, error = self.check_authentication()
        if success is False:
            return success, error

        if self.input == {}:
            return False, "Please provide valid Json request"

        for field in self.schema:
            parts = field.split("--")
            value = self.input.copy()

            # Break down nested objects
            for part in parts:
                value = value.get(part)

            valueType = type(value)
            datatypes = self.define_acceptable_datatypes(self.schema[field])

            # Dealing with Enums
            if "enum" in datatypes:
                if any([value == x for x in self.schema[field]["options"]]):
                    continue
                elif self.schema[field]["required"]:
                    return False, "One of these values - %s is required for %s" % (
                    str(self.schema[field]["options"]), field)

                elif value is None:
                    continue
                else:
                    return False, "One of these values - %s is required for %s" % (
                    str(self.schema[field]["options"]), field)

            # Dealing with pure data types (inc nulls)
            elif any([valueType.__name__ == x for x in datatypes]):
                continue

            # Dealing with None in non-required data types
            elif value is None and self.schema[field]["required"] is False:
                continue

            # If no match there is a problem
            else:
                return False, "%s should be of type %s" % (field, str(datatypes))

        return True, ""

    def define_acceptable_datatypes(self, definition):
        """
        Adds None as an acceptable data type if the field is not required

        :param definition: the value of the schema object
        :return: a list of acceptable data types as in string format
        """
        if definition["required"] is False:
            return ["None", definition["data_type"]]
        else:
            return [definition["data_type"]]