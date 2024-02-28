import json
import os.path
import urllib.parse

import scrapy


class WaybackMachineSpider(scrapy.Spider):
    name = "wbm"

    cdx_api_url = "https://web.archive.org/cdx/search/xd"
    cdx_columns = ["timestamp", "original", "mimetype"]
    good_mimetypes = set(
        [
            "text/html",
            "text/css",
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
            "image/svg+xml",
            "application/javascript",
        ]
    )

    def __init__(
        self, domains=None, domain_file=None, root="downloaded", *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.root = root

        self.start_urls = []

        if domains:
            domains = domains.split(",")
            self.start_urls.extend(domains)

        if domain_file:
            with open(domain_file) as fd:
                domains = [line.strip() for line in fd]
            self.start_urls.extend(domains)

    def start_requests(self):
        """
        First get a list of urls from wayback machine's CDX API. Then filter by latest timestamp. Then filter by extension (HTML, CSS, images, Javascript). Then yield from that list.
        """
        for url in self.start_urls:
            params = {
                "url": url,
                "output": "json",
                "gzip": "false",
                "fl": ",".join(self.cdx_columns),
                "filter": "statuscode:200",
                "matchType": "host",
            }
            # You might think that these values should be url-encoded. You are wrong. The CDX server doesn't want to see any %20 in this request.
            params = "&".join(f"{key}={value}" for key, value in params.items())

            yield scrapy.Request(
                f"{self.cdx_api_url}?{params}", callback=self.parse_cdx
            )

    def parse_cdx(self, response):
        """
        Parses response from CDX API and yields many general requests to actually download content.
        """
        body = json.loads(response.text)

        # First row is column headers
        if body[0] == self.cdx_columns:
            body.pop(0)

        timestamps = {}

        for timestamp, url, mimetype in body:
            if mimetype not in self.good_mimetypes:
                # self.logger.debug("Skipping bad mimetype '%s' (%s)", mimetype, url)
                continue

            url = urllib.parse.urlparse(url)._replace(params="", query="", fragment="")

            if url not in timestamps:
                timestamps[url] = timestamp

            if timestamp > timestamps[url]:
                timestamps[url] = timestamp

        for url, timestamp in timestamps.items():
            yield scrapy.Request(
                f"https://web.archive.org/web/{timestamp}id_/{url.geturl()}",
                callback=self.parse,
                meta=dict(wayback_machine_orig_url=url.geturl()),
            )

    def parse(self, response):
        url = response.meta["wayback_machine_orig_url"]
        url = urllib.parse.urlparse(url)
        diskpath = self.get_diskpath(url)

        dirname = os.path.dirname(diskpath)
        os.makedirs(dirname, exist_ok=True)

        with open(diskpath, "wb") as fd:
            fd.write(response.body)

    def get_diskpath(self, url):
        path = url.path
        domain = url.netloc

        # Directory
        if path.endswith("/"):
            path += "index.html"

        name, ext = os.path.splitext(path)
        if not ext:
            path += ".html"

        path = path.lstrip("/")

        # Join with the domain
        return os.path.join(self.root, domain, path)
