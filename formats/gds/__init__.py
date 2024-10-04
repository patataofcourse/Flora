import click
import contextlib
import collections
import sys
import os

import formats.gds.cmddef as cmddef
import formats.gds.gds as gds
import formats.gds.gda as gda
import formats.gds.patch as patch
from utils import cli_file_pairs, foreach_file_pair

cmddef.init_commands()


@click.group(
    help="Script-like format, also used to store puzzle parameters.", options_metavar=""
)
def cli():
    pass


@cli.command(name="compile", no_args_is_help=True)
@click.argument("input", required=False, type=click.Path(exists=True))
@click.argument("output", required=False, type=click.Path(exists=False))
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Recurse into subdirectories of the input directory to find more applicable files.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress all output. By default, operations involving multiple files will show a progressbar.",
)
@click.option(
    "--overwrite/--no-overwrite",
    "-o/-O",
    default=True,
    help="Whether existing files should be overwritten. Default: true",
)
@click.option(
    "--workspace",
    "-w",
    type=click.Path(dir_okay=True, file_okay=False, exists=True),
    help="The path to the workspace directory, i.e. the root folder into which the NDS ROM was extracted. "
    "Paths in scripts are relative to this. If unset, defaults to the current working directory (usually not what you want).",
)
def gds_compile(input=None, output=None, recursive=False, quiet=False, overwrite=None, workspace=None):
    """
    Compiles the human-readable script(s) at INPUT into the game's binary script files at OUTPUT.

    INPUT can be a single file or a directory (which obviously has to exist). In the latter case subfiles with the correct file ending will be processed.
    If unset, defaults to the current working directory.

    The meaning of OUTPUT may depend on INPUT:
    - If INPUT is a file, then OUTPUT is expected to be a file, unless it explicitly ends with a slash indicating a directory.
      In this case, if unset OUTPUT will default to the INPUT filename with `.gds` exchanged/appended.
    - Otherwise OUTPUT has to be a directory as well (or an error will be shown).
      In this case, if unset OUTPUT will default to the INPUT directory (which may itself default to the current working directory).

    In the file-to-file case, the paths are explicitly used as they are. Otherwise, if multiple input files were collected, or OUTPUT is a directory,
    an output path is inferred for each input file by exchanging the input format's file ending for, or otherwise appending the `.gds` file ending.

    In the case where INPUT is a directory, if no format is specified, this command will collect all files with ending `.gda`.
    """
    workdir = workspace or os.getcwd()

    def process(inpath, outpath):
        with open(inpath, "r", encoding="utf-8") as inf:
            filename = os.path.relpath(inpath, workdir)
            prog = gda.read_gda(inf.read(), filename)

        with open(outpath, "wb") as outf:
            outf.write(gds.write_gds(prog))

    pairs = cli_file_pairs(
        input, output, in_endings=[".gda"], out_ending=".gds", recursive=recursive
    )

    duplicates = collections.defaultdict(list)
    for ip, op in pairs:
        duplicates[op].append(ip)
    duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}
    if duplicates:
        print(
            f"ERROR: {len(duplicates)} {'files have' if len(duplicates) > 1 else 'file has'} multiple conflicting source files; please explicitly specify a format to determine which should be used.",
            file=sys.stderr,
        )
        for op, ips in duplicates.items():
            pathlist = ", ".join(f"'{ip}'" for ip in ips)
            print(f"'{op}' could be compiled from {pathlist}", file=sys.stderr)
        sys.exit(-1)

    if not overwrite:
        new_pairs = []
        existing = []
        for ip, op in pairs:
            if os.path.exists(op):
                existing.append(op)
            else:
                new_pairs.append((ip, op))

        if not quiet:
            print(f"Skipping {len(existing)} existing output files.")

        pairs = new_pairs

    foreach_file_pair(pairs, process, quiet=quiet)


@cli.command(name="decompile", no_args_is_help=True)
@click.argument("input", required=False, type=click.Path(exists=True))
@click.argument("output", required=False, type=click.Path(exists=False))
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Recurse into subdirectories of the input directory to find more applicable files.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress all output. By default, operations involving multiple files will show a progressbar.",
)
@click.option(
    "--overwrite/--no-overwrite",
    "-o/-O",
    default=True,
    help="Whether existing files should be overwritten. Default: true",
)
@click.option(
    "--workspace",
    "-w",
    type=click.Path(dir_okay=True, file_okay=False, exists=True),
    help="The path to the workspace directory, i.e. the root folder into which the NDS ROM was extracted. "
    "Paths in scripts are relative to this. If unset, defaults to the current working directory (usually not what you want).",
)
@click.option(
    "--patches/--no-patches",
    "-p/-P",
    default=True,
    help="Whether to apply 'baseline patches' that fix known errors in the vanilla scripts. Which patch to apply is determined "
    "by the filename relative to the workspace directory. Default: true; note that some of the vanilla scripts WILL NOT PARSE without "
    "these patches, so when in doubt, keep it enabled."
)
def gds_decompile(
    input=None, output=None, recursive=False, quiet=False, overwrite=None, workspace=None, patches=None
):
    """
    Decompiles the GDS script(s) at INPUT into the human-readable GDA script format at OUTPUT.

    INPUT can be a single file or a directory (which obviously has to exist). In the latter case subfiles with the correct file ending will be processed.
    If unset, defaults to the current working directory.

    The meaning of OUTPUT may depend on INPUT:
    - If INPUT is a file, then OUTPUT is expected to be a file, unless it explicitly ends with a slash indicating a directory.
      In this case, if unset OUTPUT will default to the INPUT filename with `.gda` exchanged/appended.
    - Otherwise OUTPUT has to be a directory as well (or an error will be shown).
      In this case, if unset OUTPUT will default to the INPUT directory (which may itself default to the current working directory).

    In the file-to-file case, the paths are explicitly used as they are. Otherwise, if multiple input files were collected, or OUTPUT is a directory,
    an output path is inferred for each input file by exchanging the `.gds` file ending for `.gda`, or otherwise appending the `.gda` file ending.
    """
    # TODO: once/if workspaces are a thing, use auto-discovery to place the file in the workspace correctly
    workdir = workspace or os.getcwd()

    def process(inpath, outpath):
        try:
            filepath = os.path.relpath(inpath, workdir)
            with open(inpath, "rb") as inf:
                indata = inf.read()
            if patches:
                indata = patch.patch(indata, filepath)
            prog = gds.read_gds(indata, inpath)

            with open(outpath, "w", encoding="utf-8") as outf:
                # TODO: determine the working directory? somehow??
                outf.write(gda.write_gda(prog, filepath, workdir))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"ERR: {inpath}: could not decompile: {e}")

    pairs = cli_file_pairs(
        input, output, in_endings=[".gds"], out_ending=".gda", recursive=recursive
    )
    if not overwrite:
        new_pairs = []
        existing = []
        for ip, op in pairs:
            if os.path.exists(op):
                existing.append(op)
            else:
                new_pairs.append((ip, op))

        if not quiet:
            print(f"Skipping {len(existing)} existing output files.")

        pairs = new_pairs
    foreach_file_pair(pairs, process, quiet=quiet)
