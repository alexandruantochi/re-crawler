import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from datetime import date


class OlxReRoSpider(scrapy.Spider):
    name = 'olx-re-ro'
    ad_types = ['apartamente-garsoniere-de-vanzare'] #,'apartamente-garsoniere-de-inchiriat']
    allowed_domains = ['olx.ro', 'storia.ro']
    start_urls = [ x.format(y) for y in ad_types for x in [
        'https://www.olx.ro/imobiliare/{}/iasi_39939/?search%5Border%5D=created_at%3Adesc&currency=EUR',
        'https://www.olx.ro/imobiliare/{}/cluj-napoca/?search%5Border%5D=created_at%3Adesc&currency=EUR',
        'https://www.olx.ro/imobiliare/{}/timisoara/?search%5Border%5D=created_at%3Adesc&currency=EUR',
        'https://www.olx.ro/imobiliare/{}/brasov/?search%5Border%5D=created_at%3Adesc&currency=EUR',
        'https://www.olx.ro/imobiliare/{}/constanta/?search%5Border%5D=created_at%3Adesc&currency=EUR'
    ]]

    storia_meta = {
        'surface': 'Suprafata construita (m²)',
        'rooms': 'Numarul de camere',
        'floor': 'Etaj',
        'built': 'Anul constructiei'
    }

    olx_meta = {
        'Suprafata utila': 'surface',
        'Numarul de camere': 'rooms',
        'Etaj': 'floor',
        'An constructie': 'build',
        'Persoana fizica': True,
        'Firma': False
    }

    def parse(self, response, **kwargs):

        ads = response.css("div.offer-wrapper")
        ad_city = response.url.split('/?search')[0].split('/')[-1]
        yesterday_ads_seen = False
        promo_count = 0
        for ad in ads:
            ad_time = ad.xpath(
                ".//i[@data-icon='clock']/../text()").extract_first()
            # we have today or yesterday ads in our list
            yesterday_ads_seen = 'Ieri' in ad_time or 'Azi' in ad_time

            if 'Ieri' in ad_time:
                ad_link = ad.css("a.detailsLink::attr(href)").extract_first()
                # ad is a promoted add, skip
                if ad_link is None:
                    promo_count += 1
                    continue

                ad_source = 'storia' if 'storia.ro' in ad_link else 'olx'
                yield response.follow(ad_link, self.parse_listing, cb_kwargs={'ad_source': ad_source, 'ad_city': ad_city})
            
        if yesterday_ads_seen:
            # all ads were promoted
            yield scrapy.Request(self.get_next_page(response), self.parse)

    def parse_listing(self, response, **kwargs):

        if kwargs['ad_source'] == 'olx':
            extractor = self.get_olx_data
        else:
            extractor = self.get_storia_data

        listing = extractor(response)
        listing['listed'] = date.today().isoformat()
        listing['sqm_price'] = self.get_price_per_sqm(
            listing['surface'], listing['price'])

        for key in kwargs.keys():
            listing[key] = kwargs[key]

        yield listing

    def get_next_page(self, response):
        split_url = response.url.split('&page=')
        base_page_url = split_url[0]
        if len(split_url) > 1:
            page_number = int(split_url[-1])
        else:
            page_number = 1

        return base_page_url + f'&page={page_number+1}'

    def get_olx_data(self, response):
        listing = {}
        listing['price'] = self.get_number(response.css(
            'div[data-testid="ad-price-container"] > h3::text').extract_first())
        info = response.css('ul > li > p::text').extract()

        for entry in info:
            key_value_entry = entry.split(': ')
            # no key, just value (e.g. Firma, Persoana fizica, unknown)
            if len(key_value_entry) == 1:
                # key for company or private person
                if key_value_entry[0] in ['Firma', 'Persoana fizica']:
                    listing['private'] = 'Firma' not in key_value_entry
                else:
                    # single key, no value, unknown key -> skip
                    continue
            else:
                _key, _value = key_value_entry
                if _key in OlxReRoSpider.olx_meta:
                    listing[OlxReRoSpider.olx_meta[_key]] = _value

        return listing

    def get_storia_data(self, response):

        listing = {
            'price': self.get_number(response.css('strong[data-cy="adPageHeaderPrice"]::text').extract_first()),
            'private': 'NA',
            'rooms': self.get_storia_info(response, OlxReRoSpider.storia_meta['rooms']),
            'surface': self.get_storia_info(response, OlxReRoSpider.storia_meta['surface']),
            'floor': self.get_storia_info(response, OlxReRoSpider.storia_meta['floor']),
            'built': self.get_storia_info(response, OlxReRoSpider.storia_meta['built']),
        }

        return listing

    def get_storia_info(self, response, div_title):
        info = response.css(
            f'div[title="{div_title}"] ~ div::text').extract_first()
        return info or 'NA'

    def get_number(self, number_to_parse):
        allowed_chars = ',.'
        if not number_to_parse:
            return ''
        return ''.join([c for c in number_to_parse if (c.isdecimal() or c in allowed_chars)])

    def get_price_per_sqm(self, surface, price):
        surface = self.get_number(surface).replace(',', '.')
        return round(float(price) / float(surface))
