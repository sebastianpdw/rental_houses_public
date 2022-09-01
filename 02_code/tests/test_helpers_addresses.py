from loguru import logger as lg

from helpers.addresses import extract_zipcode, parse_address_str


class TestHelpersAddresses:

    def test_extract_zipcode(self):
        """
        Test the zipcode parser
        """
        test_dict = {"1234AB": True,
                     "1234 AB": True,
                     "1234   AB": True,
                     "123AB": False,
                     "foo": False}
        for zip_code, expected_a_result in test_dict.items():
            parsed_zipcode = extract_zipcode(zip_code)
            if parsed_zipcode:
                found_result = True
            else:
                found_result = False
            lg.debug("Parsed zipcode as address: %s" % parsed_zipcode)
            assert found_result == expected_a_result

    def test_parse_address(self):
        """
        Test the address parser
        """
        test_dict = {"Utrecht Centraal Station": True,
                     "Laan van Nieuw-Guinea Utrecht": True,
                     "BLaaaaa": False}
        for address, expected_a_result in test_dict.items():

            parsed_address = parse_address_str(address)
            if parsed_address:
                found_result = True
            else:
                found_result = False
            lg.debug("Parsed address as: %s" % parsed_address)
            assert found_result == expected_a_result
