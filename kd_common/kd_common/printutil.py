import prettyprinter
from dataclasses import dataclass

prettyprinter.install_extras(
    # Comment out any packages you are not using.
    include=[
        'dataclasses',
    ],
    warn_on_error=True
)

pprint = prettyprinter.pprint
