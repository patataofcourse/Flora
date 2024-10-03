import os
from contextlib import contextmanager, suppress
from typing import (Any, Callable, Generic, Mapping, TypeVar, Union,
                    get_origin, get_type_hints)


def cli_file_pairs(
    input=None,
    output=None,
    *,
    in_endings=None,
    out_ending=None,
    filter_infer=None,
    recursive=False,
):
    """
    Given the file path inputs to the various CLI commands, determines which input files should be operated on and mapped to which output files.

    Input paths are handled as follows:
    - If the input is a file, that file will be used.
    - If the input is a directory, all files in this directory (with the file ending `in_ending`) will be separately treated as input paths.
    - If there is no input (which also means there's no output), the current working directory is used as both input and output
      (which should be fine since most commands produce files of a different ending).

    Assuming the input is a file, then if the output is the same this pair is used as-is. Otherwise, if the output isn't specified (or a directory)
    he output path is *inferred* like this:
        - If the input ends with the expected file ending, that is stripped and replaced with the output file ending.
          It's expected that if a user wants more control over this file extension, they should provide an output manually for each input file.
        - If the input has a different ending (or none at all), the output file ending is simply appended to the full name.

    This same inference is used if the input is a directory: here we have multiple input paths, for which the targets can not have been specified,
    and so the inference is applied to each of them separately. The output must be a directory (or the input directory itself if not specified) and
    all the output paths are calculated such that input paths relative to the input directory become output paths relative to the output directory
    (i.e. `in/a/b/c.input` becomes `out/a/b/c.output`). If the output exists but isn't a directory, the CLI exits with an error explaining how this doesn't make sense.
    """

    if input is None:
        input = "."

    if not os.path.exists(input):
        raise FileNotFoundError(input)

    def listfiles(path):
        if recursive:
            for dp, _, fn in os.walk(path, topdown=True):
                for f in fn:
                    yield os.path.join(dp, f)
        else:
            for f in os.listdir(path):
                if not os.path.isfile(os.path.join(path, f)):
                    continue
                yield os.path.join(path, f)

    def default_filter_infer(input, force_accept=False):
        if in_endings is not None and not any(
            input.lower().endswith(ie) for ie in in_endings
        ):
            return None
        if out_ending is not None and input.lower().endswith(out_ending):
            return None

        output = input
        if in_endings is not None:
            endings = [ie for ie in in_endings if input.lower().endswith(ie)]
            if endings:
                output = input[: -len(endings[0])]
        if out_ending is None:
            raise ValueError(
                "Can't infer output file names without a target file ending specified"
            )
        output += out_ending
        return output

    if filter_infer is None:
        filter_infer = default_filter_infer

    input_dir = ""
    input_paths = []
    rel_pairs = None
    if os.path.isfile(input):
        input_dir, ip = os.path.split(input)
        input_paths = [ip]
        rel_pairs = [(ip, filter_infer(ip, force_accept=True)) for ip in input_paths]
    else:
        input_dir = input
        input_paths = [os.path.relpath(f, input_dir) for f in listfiles(input)]
        rel_pairs = [(ip, filter_infer(ip)) for ip in input_paths]
    rel_pairs = [(ip, op) for (ip, op) in rel_pairs if op is not None]

    if output is None:
        output = input_dir

    if (
        os.path.isfile(input)
        and not os.path.isdir(output)
        and os.path.split(output)[1] != ""
    ):
        return [(input, output)]

    if os.path.isfile(output):
        raise OSError(f"Output path exists but is not a directory: '{output}'")
    output_dir = output

    pairs = [
        (os.path.join(input_dir, ip), os.path.join(output_dir, op))
        for (ip, op) in rel_pairs
    ]
    return pairs


def foreach_file_pair(pairs, fn, quiet=False):
    try:
        from tqdm import tqdm

        if not quiet and len(pairs) > 5:
            progress = tqdm(pairs)
            for input, output in progress:
                progress.set_description(input)
                fn(input, output)
            return
    except ImportError:
        # TQDM isn't installed; just don't show a progress bar.
        pass
    for input, output in pairs:
        fn(input, output)

T = TypeVar('T')
class TU(Generic[T]):
    union: type
    name: str

    def __init__(self, union: type, name: str):
        self.union = union
        self.name = name

    def __call__(self, val=None) -> "TUI[T]":
        # assert isinstance(val, T)
        return TUI(self, val)

    def __contains__(self, other):
        return other.variant == self if isinstance(other, TUI) else False

    # def __eq__(self, other):
    #     return self.union == other.union and self.name == other.name

    def __hash__(self):
        return hash((self.union, self.name))

    def __repr__(self):
        return f"{self.union.__name__}.{self.name}"

class TUI(Generic[T]):
    variant: TU[T]
    value: T

    def __init__(self, variant: TU[T], value: T):
        self.variant = variant
        self.value = value

    def __call__(self) -> T:
        return self.value

    def __eq__(self, other):
        return self.variant == other.variant and self.value == other.value

    def __hash__(self):
        return hash((self.variant, self.value))

    def __repr__(self):
        return f"{repr(self.variant)}({repr(self.value)})"

def tagged_union(cls: type):
    hints = get_type_hints(cls)
    members = [(k,v) for (k,v) in hints.items() if get_origin(v) == TU]
    
    for (name, t) in members:
        setattr(cls, name, t(cls, name))
    
    return cls

class Test:
    a: TU[int]
    b: TU[str]

R = TypeVar('R')
def match(union: TUI, fns: Mapping[Union[TU, type(...)], Callable[[Any],R]]) -> R:
    ellipsis_fn = None
    for k,v in fns.items():
        if k is Ellipsis:
            ellipsis_fn = v
            continue
        if union in k:
            return v(union())
    if ellipsis_fn is not None:
        return ellipsis_fn()

RESOURCES = os.path.join(os.path.dirname(__file__), "data")


@contextmanager
def nested_break():
    """
    Raise the returned value to instantly bail out of the with block.
    Replaces loop labels for breaking out of nested iterations.
    """
    class NestedBreakException(Exception):
        pass
    with suppress(NestedBreakException):
        yield NestedBreakException
