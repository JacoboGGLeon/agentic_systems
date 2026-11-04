# Configuration equivalent mutations

Four generated mutations survive the configuration-module reevaluation. None is excluded from the gate.

- `x_framework__mutmut_7` and `__mutmut_10` skip converting absent option arguments from None to {} in the factory. The _Framework before-validator options_are_mappings independently converts None to {}, before boundary validation and storage. Both paths therefore produce identical normalized options.
- `x_model_server__mutmut_37` removes the maxsplit argument from split('=', 1); `__mutmut_40` changes it to 2. The code consumes only element zero. For every string, splitting at the first equals sign, at two equals signs or at every equals sign produces the same element zero. Argument type validation is unchanged and short-circuits before splitting nonstrings.

These arguments apply to the current implementation and must be revisited if normalization or argument parsing changes. They justify equivalence, not a passing mutation gate.
