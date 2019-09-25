# Copyright 2019 Patrick Kidger. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========================================================================
"""Provides a set of commands for running tests, building documentation etc.

Find out more by running python command.py --help
"""


import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import webbrowser
#### DO NOT IMPORT NON-(STANDARD LIBRARY) MODULES HERE
# Instead, lazily import them inside the command.
# This allows all the commands that don't e.g. require a built version of Signatory to operate without it
# Exception: metadata, as we guarantee that that will not import anything that isn't standard library.
import metadata


def main():
    deviceparser = argparse.ArgumentParser(add_help=False)
    deviceparser.add_argument('-d', '--device', type=int, default=-1,
                              help="Which CUDA device to use, from a range of 0 upwards. May be set to -1 to not "
                                   "try to change the default device e.g. if no CUDA device is available. Defaults to "
                                   "-1.")

    parser = argparse.ArgumentParser(description="Runs various commands for building and testing Signatory.")
    parser.add_argument('-v', '--version', action='version', version=metadata.version)
    subparsers = parser.add_subparsers(dest='command', help='Which command to run')
    
    test_parser = subparsers.add_parser('test', parents=[deviceparser], description="Run tests")
    benchmark_parser = subparsers.add_parser('benchmark', parents=[deviceparser], description="Run speed benchmarks")
    docs_parser = subparsers.add_parser('docs', description="Build documentation")
    genreadme_parser = subparsers.add_parser('genreadme', description="Generate the README from the documentation.")

    test_parser.set_defaults(cmd=test)
    benchmark_parser.set_defaults(cmd=benchmark)
    docs_parser.set_defaults(cmd=docs)
    genreadme_parser.set_defaults(cmd=genreadme)

    test_parser.add_argument('-f', '--failfast', action='store_true', help='Stop tests on first failure.')
    test_parser.add_argument('-n', '--nonames', action='store_false', dest='names',
                             help="Don't print names and start time of the tests being run.")
    test_parser.add_argument('-t', '--notimes', action='store_false', dest='times',
                             help="Don't print the overall times of the tests that have been run.")

    benchmark_parser.add_argument('-e', '--noesig', action='store_false', dest='test_esig',
                                  help="Skip esig tests as esig is typically very slow.")
    benchmark_parser.add_argument('-g', '--nogpu', action='store_false', dest='test_signatory_gpu',
                                  help="Skip Signatory GPU tests, (perhaps if you don't have a GPU installed).")
    benchmark_parser.add_argument('-a', '--ratio', action='store_false',
                                  help="Skip computing and plotting the improvement ratio of Signatory over "
                                       "iisignature or esig.")
    benchmark_parser.add_argument('-m', '--measure', choices=('time', 'memory'), default='time',
                                  help="Whether to measure speed or memory usage.")
    benchmark_parser.add_argument('-f', '--fns', choices=('sigf', 'sigb', 'logsigf', 'logsigb', 'all'), default='all',
                                  help="Which functions to run: signature forwards, signature backwards, logsignature "
                                       "forwards, logsignature backwards, or all of them.")
    benchmark_parser.add_argument('-t', '--type', choices=('typical', 'depths', 'channels', 'small'), default='typical',
                                  help="What kind of benchmark to run. 'typical' tests on two typical size/depth "
                                       "combinations and prints the results as a table to stdout. 'depth' and "
                                       "'channels' are more thorough benchmarks (and will taking correspondingly "
                                       "longer to run!) testing multiple depths or multiple channels respectively.")
    benchmark_parser.add_argument('-o', '--output', choices=('table', 'graph', 'none'), default='table',
                                  help="How to format the output. 'table' formats as a table, 'graph' formats as a "
                                       "graph. 'none' prints no output at all (perhaps if you're retrieving the results"
                                       " programmatically by importing command.py instead).")
                                  
    docs_parser.add_argument('-o', '--open', action='store_true',
                             help="Open the documentation in a web browser as soon as it is built.")

    args = parser.parse_args()

    # Have to do it this way for Python 2/3 compatability
    if hasattr(args, 'cmd'):
        return args.cmd(args)
    else:
        # No command was specified
        print("Please enter a command. Use -h to see available commands.")


here = os.path.realpath(os.path.dirname(__file__))


def get_device():
    import torch
    try:
        return 'CUDA device ' + str(torch.cuda.current_device())
    except AssertionError:
        return 'no CUDA device'


class NullContext(object):
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test(args):
    """Run all tests.
    The package 'iisignature' will need to be installed, to test against.
    It can be installed via `pip install iisignature`
    """
    try:
        import iisignature  # fail fast here if necessary
    except ImportError:
        raise ImportError("The iisignature package is required for running tests. It can be installed via 'pip "
                          "install iisignature'")
    import test.runner
    import torch
    with torch.cuda.device(args.device) if args.device != -1 else NullContext():
        print('Using ' + get_device())
        test.runner.main(failfast=args.failfast, times=args.times, names=args.names)


def benchmark(args):
    """Run speed benchmarks."""
    try:
        import iisignature  # fail fast here if necessary
    except ImportError:
        raise ImportError("The iisignature package is required for running tests. It can be installed via 'pip "
                          "install iisignature'")
    try:
        import esig  # fail fast here if necessary
    except ImportError:
        raise ImportError("The esig package is required for running tests. It can be installed via 'pip "
                          "install esig'")
                          
    import test.benchmark as bench
    import torch
    with torch.cuda.device(args.device) if args.device != -1 else NullContext():
        print('Using ' + get_device())
        if args.type == 'typical':
            runner = bench.BenchmarkRunner.typical(ratio=args.ratio,
                                                   test_esig=args.test_esig,
                                                   test_signatory_gpu=args.test_signatory_gpu,
                                                   measure=args.measure,
                                                   fns=args.fns)
        elif args.type == 'depths':
            runner = bench.BenchmarkRunner.depths(ratio=args.ratio,
                                                  test_esig=args.test_esig,
                                                  test_signatory_gpu=args.test_signatory_gpu,
                                                  measure=args.measure,
                                                  fns=args.fns)
        elif args.type == 'channels':
            runner = bench.BenchmarkRunner.channels(ratio=args.ratio,
                                                    test_esig=args.test_esig,
                                                    test_signatory_gpu=args.test_signatory_gpu,
                                                    measure=args.measure,
                                                    fns=args.fns)
        elif args.type == 'small':
            runner = bench.BenchmarkRunner.small(ratio=args.ratio,
                                                 test_esig=args.test_esig,
                                                 test_signatory_gpu=args.test_signatory_gpu,
                                                 measure=args.measure,
                                                 fns=args.fns)
        else:
            raise RuntimeError
        if args.output == 'graph':
            runner.check_graph()
        runner.run()
        if args.output == 'graph':
            runner.graph()
        elif args.output == 'table':
            runner.table()
        elif args.output == 'none':
            pass
        else:
            raise RuntimeError
    return runner

    
def docs(args=()):
    """Build the documentation. After it has been built then it can be found in ./docs/_build/html/index.html/
    The package 'py2annotate' will need to be installed. It can be installed via `pip install py2annotate`
    Note that the documentation is already available online at https://signatory.readthedocs.io
    """
    try:
        import py2annotate  # fail fast here if necessary
    except ImportError:
        raise ImportError("The py2annotate package is required for running tests. It can be installed via 'pip "
                          "install py2annotate'")
    try:
        shutil.rmtree(os.path.join(here, "docs", "_build"))
    except FileNotFoundError:
        pass
    subprocess.Popen("sphinx-build -M html {} {}".format(os.path.join(here, "docs"), os.path.join(here, "docs", "_build"))).wait()
    if args.open:
        webbrowser.open_new_tab('file:///{}'.format(os.path.join(here, 'docs', '_build', 'html', 'index.html')))

    
def genreadme(args=()):
    """The readme is generated automatically from the documentation."""
    
    outs = []
    includestr = '.. include::'
    on = '.. genreadme on'
    off = '.. genreadme off'
    insert = '.. genreadme insert '  # space at end is important
    reference = re.compile(r'^\.\. [\w-]+:$')
    
    inserts = {'install_from_source': "Installation from source is also possible; please consult the `documentation "
                                      "<https://signatory.readthedocs.io/en/latest/pages/usage/installation.html#usage-install-from-source>`__."}

    def parse_file(filename):
        out_data = []
        with io.open(filename, 'r', encoding='utf-8') as f:
            data = f.readlines()
            skipping = False
            for line in data:
                stripline = line.strip()
                if stripline == on:
                    skipping = False
                elif stripline == off:
                    skipping = True
                elif skipping:
                    pass
                elif reference.match(stripline):
                    pass
                else:
                    if stripline.startswith(insert):
                        out_line = inserts[stripline[len(insert):]]
                    elif stripline.startswith(includestr):
                        # [1:] to remove the leading / at the start; otherwise ends up being parsed as root
                        subfilename = stripline[len(includestr):].strip()[1:]
                        out_line = parse_file(os.path.join(here, 'docs', subfilename))
                    else:
                        out_line = line
                    if ':ref:' in out_line:
                        raise RuntimeError('refs not supported')
                    out_data.append(out_line)
        return ''.join(out_data)

    def read_from_files(filenames):
        for filename in filenames:
            filename = os.path.join(here, filename)
            outs.append(parse_file(filename))

    read_from_files([os.path.join(here, 'docs', 'index.rst'),
                     os.path.join(here, 'docs', 'pages', 'understanding', 'whataresignatures.rst'),
                     os.path.join('docs', 'pages', 'usage', 'installation.rst')])

    outs.append("Documentation\n"
                "#############\n"
                "The documentation is available `here <https://signatory.readthedocs.io>`__.")

    read_from_files([os.path.join(here, 'docs', 'pages', 'miscellaneous', 'citation.rst'),
                     os.path.join(here, 'docs', 'pages', 'miscellaneous', 'acknowledgements.rst')])

    with io.open(os.path.join(here, 'README.rst'), 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(outs))


def should_not_import(args=()):
    """Tests that we _can't_ import Signatory. Doing this before we install it ensures that we're definitely testing
    the version we install and not some other version we can accidentally see.
    """

    try:
        import signatory
    except ImportError as e:
        if str(e) == 'No module named signatory':
            return True
        else:
            return False
    else:
        return False
        
            
if __name__ == '__main__':
    result = main()
    if result is not None:
        if not result:
            sys.exit(1)
