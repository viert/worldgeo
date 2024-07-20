import pycountry
from dataclasses import dataclass


@dataclass
class Country:
    code2: str
    code3: str
    name: str
    flag: str
    numeric: str

    @classmethod
    def construct(cls, name: str, code: str):
        pcc = pycountry.countries.get(alpha_3=code)
        print(pcc)
