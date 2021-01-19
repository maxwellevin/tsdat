import numpy as np
from typing import Any, Dict, List, Tuple
from .attribute_defintion import AttributeDefinition
from .dimension_definition import DimensionDefinition

class VarKeys:
    INPUT = 'input'
    DIMS = 'dims'
    TYPE = 'type'
    ATTRS = 'attrs'

class VarInputKeys:
    NAME = 'name'
    TIME_FORMAT = 'time_format'

class VarInput:    
    """-----------------------------------------------------------------------
    Class to explicitly encode fields set by the variable's input source 
    defined by the yaml file.
    -----------------------------------------------------------------------"""
    def __init__(self, dictionary: Dict):
        self.name: str = dictionary[VarInputKeys.NAME]
        self.time_format: str = dictionary.get(VarInputKeys.TIME_FORMAT, None)

class VariableDefinition:
    """-----------------------------------------------------------------------
    Class to encode variable definitions from the config file. Also provides
    a few utility methods.
    -----------------------------------------------------------------------"""
    def __init__(self, name: str, dictionary: Dict, available_dimensions: Dict[str, DimensionDefinition]):
        self.name: str = name
        self.input = self._parse_input(dictionary)
        self.attrs = self._parse_attributes(dictionary)
        self.dims = self._parse_dimensions(dictionary, available_dimensions)
        self.type = self._parse_data_type(dictionary)

        for key in dictionary:
            if not hasattr(self, key):
                setattr(self, key, dictionary[key])

        self._predefined = hasattr(self, "data")
    
    def _parse_input(self, dictionary: Dict) -> VarInput:
        input_source = dictionary.get(VarKeys.INPUT, None)
        if not input_source:
            return None
        return VarInput(input_source)
    
    def _parse_attributes(self, dictionary: Dict) -> Dict[str, AttributeDefinition]:
        attributes: Dict[str, AttributeDefinition] = {}
        for attr_name, attr_value in dictionary.get(VarKeys.ATTRS, {}).items():
            attributes[attr_name] = AttributeDefinition(attr_name, attr_value)
        return attributes

    def _parse_dimensions(self, dictionary: Dict, available_dimensions: Dict[str, DimensionDefinition]) -> Dict[str, DimensionDefinition]:
        requested_dimensions: List[str] = dictionary.get(VarKeys.DIMS, [])
        parsed_dimensions: Dict[str, DimensionDefinition] = {}
        for dim_name in requested_dimensions:
            if dim_name not in available_dimensions:
                raise KeyError(f"'{dim_name}' is not a recognized dimension. Available dimensions include: {', '.join(list(available_dimensions.keys()))}")
            parsed_dimensions[dim_name] = available_dimensions[dim_name]
        return parsed_dimensions

    def _parse_data_type(self, dictionary: Dict) -> object:
        """-------------------------------------------------------------------
        Parses the data_type string and returns the appropriate numpy data 
        type (i.e. "float" -> np.float). 

        Args:
            data_type (str): the data type as read from the yaml.

        Returns:
            Object: The numpy data type corresponding with the type provided
                    in the yaml file, or data_type if the provided data_type
                    is not in the MHKiT-Cloud Data Standards list of data 
                    types.
        -------------------------------------------------------------------"""
        data_type: str = dictionary.get(VarKeys.TYPE, "")
        mappings = {
            "string":   np.str,
            "char":     np.str,
            "byte":     np.int8,
            "ubyte":    np.uint8,
            "short":    np.int16,
            "ushort":   np.uint16,
            "long":     np.int64,
            "ulong":    np.uint64,
            "int":      np.int32,
            "float":    np.float32,
            "double":   np.float64
        }
        if data_type not in mappings:
            error_message = f"'{data_type}' is not a standard data type. Data type must be one of: \n{', '.join(list(mappings.keys()))}"
            raise KeyError(error_message)
        return mappings[data_type]

    def is_constant(self) -> bool:
        """-------------------------------------------------------------------
        Returns True if the variable is a constant. A variable is constant if
        it does not have any dimensions.

        Returns:
            bool: True if the variable is constant, False otherwise.
        -------------------------------------------------------------------"""
        return len(list(self.dims.keys())) == 0
    
    def is_predefined(self) -> bool:
        """-------------------------------------------------------------------
        Returns True if the variable's data was predefined in the config yaml 
        file.

        Returns:
            bool: True if the variable is predefined, False otherwise.
        -------------------------------------------------------------------"""
        return self._predefined

    def is_coordinate(self) -> bool:
        """-------------------------------------------------------------------
        Returns True if the variable is a coordinate variable. A variable is a 
        coordinate variable if it is dimensioned by itself.

        Returns:
            bool:   True if the variable is a coordinate variable, False 
                    otherwise.
        -------------------------------------------------------------------"""
        return [self.name] == [dim_name for dim_name in self.dims]


    def is_derived(self) -> bool:
        """-------------------------------------------------------------------
        Return True if the variable is derived. A variable is derived if it 
        does not have an input and it is not predefined.

        Returns:
            bool: True if the Variable is derived, False otherwise.
        -------------------------------------------------------------------"""
        return self.input is None and not self.is_predefined()
    
    def has_input(self) -> bool:
        """-------------------------------------------------------------------
        Return True if the variable is copied from an input dataset, 
        regardless of whether or not unit and/or naming conversions should be 
        applied.

        Returns:
            bool: True if the Variable has an input defined, False otherwise.
        -------------------------------------------------------------------"""
        return self.input is not None

    def get_input_name(self) -> str:
        """-------------------------------------------------------------------
        Returns the name of the variable in the input if defined, otherwise 
        returns None.

        Returns:
            str: The name of the variable in the input, or None.
        -------------------------------------------------------------------"""
        if not self.has_input():
            return None
        return self.input.name
    
    def get_input_units(self) -> str:
        if not self.has_input():
            return None
        output_units = self.get_output_units()
        return getattr(self.input, "units", output_units)
    
    def get_output_units(self) -> str:
        return self.attrs.get("units", "unitless")

    def get_coordinate_names(self) -> List[str]:
        """-------------------------------------------------------------------
        Returns the names of the coordinate VariableDefinition(s) that this 
        VariableDefinition is dimensioned by.

        Returns:
            List[str]: A list of dimension/coordinate variable names.
        -------------------------------------------------------------------"""
        return list(self.dims.keys())
    
    def get_shape(self) -> Tuple[int]:
        """-------------------------------------------------------------------
        Returns the shape of the data attribute on the VariableDefinition. 
        Raises a KeyError if the data attribute has not been set yet.

        Returns:
            Tuple[int]: The shape of the VariableDefinition's data, or None.
        -------------------------------------------------------------------"""
        if not hasattr(self, "data"):
            raise KeyError(f"No data has been set for variable: '{self.name}'")
        return None

    def get_data_type(self) -> Any:
        return self.type
    
    def get_FillValue(self):
        return self.attrs.get("_FillValue", -9999)

    def to_dict(self) -> Dict:
        """-------------------------------------------------------------------
        Returns the Variable as a dictionary to be used to intialize an xarray
        Dataset or DataArray.

        Returns a dictionary like (Example is for `temperature`):
        ```
        {
            "dims": ["time"], 
            "data": [], 
            "attrs": {"units": "degC"}
        }
        ```

        Returns:
            Dict: A dictionary representation of the variable.
        -------------------------------------------------------------------"""
        dictionary = {
            "dims":     [name for name, dim in self.dims.items()],
            "data":     self.data if hasattr(self, "data") else [],
            "attrs":    {attr_name: attr.value for attr_name, attr in self.attrs.items()}
        }
        return dictionary