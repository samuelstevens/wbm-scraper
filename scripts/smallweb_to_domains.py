"""
Converts the smallweb.txt file to a domains.txt file.
"""

import argparse
import os.path
import urllib.parse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("smallweb", help="Path to smallweb.txt")
    parser.add_argument(
        "--out", help="Path to output folder. Uses smallweb.txt's directory by default."
    )

    args = parser.parse_args()

    domains_txt = args.out
    if not domains_txt:
        domains_txt = os.path.join(os.path.dirname(args.smallweb), "domains.txt")

    with open(args.smallweb) as in_fd:
        with open(domains_txt, "w") as out_fd:
            for line in in_fd:
                url = urllib.parse.urlparse(line.strip())
                url = url._replace(path="", params="", query="", fragment="")
                url = urllib.parse.urlunparse(url)
                out_fd.write(url + "\n")
