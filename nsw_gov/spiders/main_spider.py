import scrapy
from ..items import NswGovItem
import re


class MainSpider(scrapy.Spider):
    name = 'main'
    allowed_domains = ['ecerts.ssc.nsw.gov.au']
    page = 1

    def __init__(self, date_from='01/01/2017', date_to='02/02/2017', *args, **kwargs):
        """
        crawl main -a date_from=01/01/2017 -a date_to=07/01/2017 -o data.json
        """
        self.date_from = date_from
        self.date_to = date_to
        super(MainSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        yield scrapy.Request(
            'https://ecerts.ssc.nsw.gov.au/eproperty/P1/eTrack/eTrackApplicationSearch.aspx?Group=DA&ResultsFunction=SSC.P1.ETR.RESULT.DA&r=SSC.P1.WEBGUEST&f=SSC.P1.ETR.SEARCH.DA',
            )

    def parse(self, response):
        yield scrapy.FormRequest(
            'https://ecerts.ssc.nsw.gov.au/eproperty/P1/eTrack/eTrackApplicationSearch.aspx?Group=DA&ResultsFunction=SSC.P1.ETR.RESULT.DA&r=SSC.P1.WEBGUEST&f=SSC.P1.ETR.SEARCH.DA',
            formdata={
                'ctl00$Content$txtDateFrom$txtText': self.date_from,
                'ctl00$Content$txtDateTo$txtText': self.date_to,
                'ctl00$Content$ddlApplicationType$elbList': 'all',
                'ctl00$Content$btnSearch': 'Search',
                '__EVENTTARGET': 'ctl00$Content$cusResultsGrid$repWebGrid$ctl00$grdWebGridTabularView',
                "__VIEWSTATE": response.xpath('//input[@id="__VIEWSTATE"]/@value').extract_first(),
                "__VIEWSTATEGENERATOR": response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').extract_first(),
                "__SCROLLPOSITIONX": response.xpath('//input[@id="__SCROLLPOSITIONX"]/@value').extract_first(),
                "__SCROLLPOSITIONY": response.xpath('//input[@id="__SCROLLPOSITIONY"]/@value').extract_first(),
                "__EVENTVALIDATION": response.xpath('//input[@id="__EVENTVALIDATION"]/@value').extract_first()
            },
            callback=self.check_pages,
        )

    def check_pages(self, response):
        for each in response.xpath('//table[@class="grid"]').xpath('.//tr'):
            number = each.xpath('td/script/text()').extract_first()
            if number:
                pattern = re.compile('>.*/.*<')
                try:
                    search = pattern.findall(number.strip())[0][1:-1]
                    number = search
                    yield scrapy.Request(
                        'https://ecerts.ssc.nsw.gov.au/eProperty/P1/eTrack/eTrackApplicationDetails.aspx?r=SSC.P1.WEBGUEST&f=$P1.ETR.APPDET.VIW&ApplicationId=%s' % number,
                        callback=self.parse_item,
                        dont_filter=True
                    )
                except IndexError:
                    pass

        next_page = self.page + 1
        pattern = re.compile('>%s<' % next_page)
        self.logger.info('Parsing page #%s' % self.page)
        try:
            search = pattern.findall(response.text)[0][1:-1]
            self.page = int(search)
        except IndexError:
            return
        if 'Page$%s' % self.page in response.text:
            payload = {
                "__EVENTTARGET": "ctl00$Content$cusResultsGrid$repWebGrid$ctl00$grdWebGridTabularView",
                "__EVENTARGUMENT": "Page$%s" % self.page,
                "__VIEWSTATE": response.xpath('//input[@id="__VIEWSTATE"]/@value').extract_first(),
                "__VIEWSTATEGENERATOR": response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').extract_first(),
                "__SCROLLPOSITIONX": response.xpath('//input[@id="__SCROLLPOSITIONX"]/@value').extract_first(),
                "__SCROLLPOSITIONY": response.xpath('//input[@id="__SCROLLPOSITIONY"]/@value').extract_first(),
                "__EVENTVALIDATION": response.xpath('//input[@id="__EVENTVALIDATION"]/@value').extract_first()
            }
            yield scrapy.FormRequest(
                'https://ecerts.ssc.nsw.gov.au/eProperty/P1/eTrack/eTrackApplicationSearchResults.aspx?Group=DA&r=SSC.P1.WEBGUEST&f=SSC.P1.ETR.RESULT.DA',
                formdata=payload,
                callback=self.check_pages,
                dont_filter=True
            )

    def parse_item(self, response):
        item = NswGovItem()
        # item['number'] = response.xpath('//td[contains(text(), "Contact")]/following-sibling::td/text()').extract_first()
        item['url'] = response.url
        yield item
