import time
import pickle
import csv
import math
import re
import os
from selenium import webdriver
from abc import ABC, abstractmethod
from selenium.webdriver.common.keys import Keys

""" NOTE: to add another store, create the appropriate product and shopper classes, 
          add the store in STORES, and update the browseforme __init__"""
STORES = ["peapod"]#"star-markets","wegmans","market-basket","stop-shop"]
# Note: these are the store names as they appear in the Instacart URL
INSTACART_STORES = ['market-basket',"star-markets","wegmans","market-basket","stop-shop"]
SHOPPINGLISTFILE = 'shopping_list.txt'

MAIN_SITE = "https://instacart.com"
PEADPOD_MAIN ='https://www.peapod.com/shop/auth/login?gateway=1&redirectTo=%2F'
CHROMEDRIVER = "venv/bin/chromedriver"

LOGIN_BUTTON = "//button"
SITE_LOGIN_BUTTON = '//button[@type="submit"]'
ADD_TO_CART_BUTTON = "//button"
EMAIL_FIELD_ID = "nextgen-authenticate.all.log_in_email"
PASSWD_FIELD_ID = "nextgen-authenticate.all.log_in_password"
INSTACART_EMAIL = os.environ['INSTACART_EMAIL'] if 'INSTACART_EMAIL' in os.environ else None
INSTACART_PASSWD = os.environ['INSTACART_PASSWD'] if 'INSTACART_PASSWD' in os.environ else None

WAIT_FOR_MAIN_SITE = 5
WAIT_FOR_LOGIN_PAGE = 5
WAIT_FOR_INPUT = 2
WAIT_FOR_LOGGING_IN = 10
WAIT_FOR_SEARCH = 10
WAIT_FOR_ADD = 1
WAIT_FOR_FIRST_ADD = 5

WAIT_FOR_PEAPOD_MAIN = 5
WAIT_FOR_PEAPOD_LOGIN = 5
WAIT_FOR_PEAPOD_SEARCH = 10
PEAPOD_FIRST_ADD_WAIT = 2
PEAPOD_ADD_WAIT = 0.25
PEAPOD_ADD_UPDATE_WAIT = 3
PEAPOD_ZIP_EXTRA_WAIT = 0.25
PEAPOD_ZIP_WAIT = 10
ZIPCODE = ''

AMZN_LOGIN_WAIT = 2
AMZN_ZIPCODE_WAIT = 2
AMZN_EMAIL = os.environ['AMZN_EMAIL'] if 'AMZN_EMAIL' in os.environ else None
AMZN_PASSWD = os.environ['AMZN_PASSWD'] if 'AMZN_PASSWD' in os.environ else None
AMZN_ZIPCODE = os.environ['AMZN_ZIPCODE'] if 'AMZN_ZIPCODE' in os.environ else None

ROUND_WAIT_TIME = 3*60 # 3 minutes
ROUND_COUNT = 160 # Roughly 8 hours

NUTRITION_OPTIONS = set(['vegan','kosher','is_organic','fat_free','gluten_free','sugar_free'])
PEAPOD_NUTRITION = {'kosher':'Kosher-filter','vegan':'Dairy-Free-filter',
                    'gluten_free':'Gluten-Free-filter','is_organic':'Organic-filter',
                    'fat_free':None,'sugar_free':None}
AMZN_NUTRITION = {'kosher':'3A114321011','vegan':'3A114322011',
                    'gluten_free':'3A114329011','is_organic':'3A114320011',
                    'fat_free':None,'sugar_free':None}


# class for storing product information
class Product:
    def __init__(self,name,price,quantity,defaultQ,idx,searchTerm,nutrition=None,bunchdefaultQ=None):
        # set product name, price, index on page, total cost variable, original cost, and nutrition
        self.name = name
        self.originalPrice = price
        self.searchTerm = searchTerm
        self.price = float(re.split("[ \n]",price,1)[0])
        self.idx = idx
        self.total = None
        self.originalQuantity = quantity
        self.nutriton = nutrition
        self.desired_quantity = None

        # determine unit quantity
        price = re.split("[/ \n]",price,1)
        if quantity and not quantity.split()[0] == 'About':
            self.quantity = self.quantify(quantity,defaultQ,self.price,bunchdefaultQ) # in ounces or counts/items
        elif len(price) == 2:
            self.quantity = self.quantify(' '.join(['1',price[1]]),defaultQ,self.price,bunchdefaultQ)
        else:
            raise(Exception('no quantity found'))

        # determine unit price
        self.unit_price = self.price/self.quantity

    def __str__(self):
        return f'Name: {self.name}. Price: {self.originalPrice}. Quantity: {self.originalQuantity}'

    @staticmethod
    def quantify(quantity,defaultQ,price,bunchDefaultQ):
        # parses a quantity with units into oz
        quantity = quantity.split(" ",1)

        # special cases
        if 'each' in quantity[0] or 'item' in quantity[0] or 'ct' in quantity[0]:
            return 1.0 * defaultQ
        if 'apx' in quantity[0]:
            quantity = quantity[1].split(" ",1)

        if '/' in quantity[0]:
            q = quantity[0].split('/')
            quantity[0] = float(q[0]) / float(q[1])
        elif len(quantity) == 1:
            try:
                return float(quantity[0])
            except:
                quantity.append(quantity[0])
                quantity[0] = 1.0
        elif 'per' in quantity[0]:
            quantity[0] = 1.0
        elif 'x ' in quantity[1]: # e.g., 3 x 6 oz
            quantity[1] = quantity[1].split('x ')[1].split(" ",1)
            quantity[0] = float(quantity[0])*float(quantity[1][0])
            quantity[1] = quantity[1][1]
        elif 'at' in quantity[0] or 'At' in quantity[0]:
            quantity = [q.strip() for q in quantity[1].split('/')]
            quantity[0] = price/float(quantity[0][1:])
        else:
            quantity[0] = float(quantity[0])

        # regular units
        if 'oz' in quantity[1] or 'ounce' in quantity[1].lower():
            return quantity[0]
        if 'pt' in quantity[1] or 'pint' in quantity[1]:
            return quantity[0]*16
        if 'qt' in quantity[1] or 'quart' in quantity[1]:
            return quantity[0]*32
        if 'gal' in quantity[1] or 'gallon' in quantity[1]:
            return quantity[0]*128
        if 'lb' in quantity[1] or 'pound' in quantity[1]:
            return quantity[0]*16
        if 'each' in quantity[1] or 'item' in quantity[1] or 'ct' in quantity[1] or 'ea' in quantity[1]:
            return quantity[0] * defaultQ
        if 'bunch' in quantity[1]:
            if bunchDefaultQ:
                return quantity[0]*bunchDefaultQ
            else:
                raise Exception('Item has units bunch, but no default bunch quantity was provided')
        if 'L' in quantity[1] or 'liter' in quantity[1] or 'ltr' in quantity[1]:
            return quantity[0]*33.8
        if 'ml' in quantity[1].lower():
            return quantity[0]*33.8/1000
        if quantity[1] == 'g' or 'gram' in quantity[1]:
            return quantity[0]*0.0353
        raise Exception('Unable to parse quantity units')

    def totalCost(self,quantity):
        self.total = math.ceil(quantity/self.quantity)*self.price
        self.desired_quantity = quantity


class InstaProduct(Product):
    pass


class PeaProduct(Product):
    pass


class AmazonProduct(Product):
    pass # TODO

class Shopper(ABC):
    @abstractmethod
    def __init__(self):
        self.browser = webdriver.Chrome(CHROMEDRIVER)
        self.logged_in = False

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def search(self,_0,_1,_2,_3,_4,_5,_6):
        pass

    @abstractmethod
    def add_to_cart(self,_0,_1):
        pass

    @abstractmethod
    def close(self):
        if self.browser:
            self.browser.close()
            self.browser = None


class InstacartShopper(Shopper):
    def __init__(self):
        super().__init__()

    def login(self):
        self.browser.get(MAIN_SITE)
        time.sleep(WAIT_FOR_MAIN_SITE)

        login_btn = self.browser.find_element_by_xpath(LOGIN_BUTTON)
        if not login_btn:
            raise Exception("FAILED TO LOCATE LOGIN BUTTON ON MAIN PAGE")
        login_btn.click()
        time.sleep(WAIT_FOR_LOGIN_PAGE)

        email_field = self.browser.find_element_by_id(EMAIL_FIELD_ID)
        if not email_field:
            raise Exception("FAILED TO LOCATE EMAIL FIELD ON LOGIN PAGE")
        email_field.send_keys(INSTACART_EMAIL)
        time.sleep(WAIT_FOR_INPUT)

        passwd_field = self.browser.find_element_by_id(PASSWD_FIELD_ID)
        if not passwd_field:
            raise Exception("FAILED TO LOCATE PASSWORD FIELD ON LOGIN PAGE")
        passwd_field.send_keys(INSTACART_PASSWD)
        time.sleep(WAIT_FOR_INPUT)

        login_btn = self.browser.find_element_by_xpath(SITE_LOGIN_BUTTON)
        if not login_btn:
            raise Exception("FAILED TO LOCATE LOGIN BUTTON ON MAIN PAGE")
        login_btn.click()
        time.sleep(WAIT_FOR_LOGGING_IN)

        self.logged_in = True

    def search(self,store,nutrition,desiredItem,itemIncludes,itemExcludes,defaultQuantity,bunchDefaultQ):
        if not self.logged_in:
            self.login()

        # navigate to url for item search
        if not nutrition:
            url = "https://www.instacart.com/store/" + store + "/search_v3/" + "%20".join(desiredItem.name.split())
        else:
            url = "https://www.instacart.com/store/" + store + "/search_v3/" + "%20".join(desiredItem.name.split()) + (
                "?nutrition%5B%5D=") + "&nutrition%5B%5D=".join(nutrition)
        self.browser.get(url)
        time.sleep(WAIT_FOR_SEARCH)

        # parse out items on page
        items = self.browser.find_elements_by_class_name('item-info')
        itemsInfo = []
        for i, item in enumerate(items):
            # find item name
            try:
                itemName = item.find_element_by_class_name('full-item-name').text
            except Exception as e:
                print(
                    f'Error in finding name information in store {store} for item number {i} of product search {desiredItem}')
                print(e)
                continue

            # find  item price
            try:
                itemPrice = item.find_element_by_class_name('item-price').text[1:]
                if itemPrice == "ut of Stock":
                    continue
            except Exception as e:
                print(
                    f'Error in finding price information in store {store} for product {itemName} (item {i}) of product search {desiredItem}')
                print(e)
                continue

            # find item size
            try:
                itemSize = item.find_element_by_class_name('item-size').text
            except:
                itemSize = None

            # add product to list, if it's a valid product
            try:
                if re.search(itemIncludes, itemName.lower()) and (
                        not itemExcludes or not re.search(itemExcludes, itemName.lower())):
                    newProduct = InstaProduct(itemName, itemPrice, itemSize, defaultQuantity, i, desiredItem.name,nutrition,bunchDefaultQ)
                    newProduct.totalCost(desiredItem.quantity)
                    itemsInfo.append(newProduct)
            except Exception as e:
                print(
                    f'Error creating Product Object in {store} item {i}: {itemName} with cost {itemPrice} and quantity {itemSize}')
                print(e)
                continue
        return itemsInfo

    def add_to_cart(self,store,products):
        if not self.logged_in:
            self.login()

        # add products to cart
        for product in products:
            # navigate to url for item search
            if not product.nutrition:
                url = "https://www.instacart.com/store/" + store + "/search_v3/" + "%20".join(product.name.split())
            else:
                url = "https://www.instacart.com/store/" + store + "/search_v3/" + "%20".join(
                    product.name.split()) + (
                          "?nutrition%5B%5D=") + "&nutrition%5B%5D=".join(product.nutrition)
            self.browser.get(url)
            time.sleep(WAIT_FOR_SEARCH)

            # determine how many we want total
            numProducts = round(product.total / product.price)

            try:
                # find item
                item = self.browser.find_elements_by_class_name('item-card')[product.idx]

                if item.find_element_by_class_name('full-item-name').text != product.name:
                    print(f'ERROR: {product} isn\'t where it was earlier. Please add to cart manually.')
                    continue

                # add first item to cart
                item.find_elements_by_tag_name('button')[0].click()
                time.sleep(WAIT_FOR_FIRST_ADD)

                # find button for adding product
                button = item.find_elements_by_tag_name('button')
                try:
                    # click button to allow adding items, if needed
                    if len(button) == 1:
                        item.find_elements_by_tag_name('button')[0].click()
                        time.sleep(WAIT_FOR_ADD)
                        button = item.find_elements_by_tag_name('button')
                    button = button[1]

                    # add products until reached desired quantity
                    while float(item.find_element_by_xpath('div/span').text.split()[1]) < numProducts:
                        button.click()
                # maybe a temporary overlay
                except:
                    try:
                        self.browser.find_element_by_class_name('ReactModal__Overlay').find_element_by_tag_name(
                            'button').click()
                        if len(button) == 1:
                            item.find_elements_by_tag_name('button')[0].click()
                            time.sleep(WAIT_FOR_ADD)
                            button = item.find_elements_by_tag_name('button')
                        button = button[1]
                    # maybe reloading page will fix it
                    except:
                        self.browser.get(url)
                        time.sleep(WAIT_FOR_SEARCH)

                        # find item
                        item = self.browser.find_elements_by_class_name('item-card')[product.idx]

                        if item.find_element_by_class_name('full-item-name').text != product.name:
                            print(f'ERROR: {product} isn\'t where it was earlier. Please add to cart manually.')
                            continue

                        # click button to allow adding items
                        item.find_elements_by_tag_name('button')[0].click()
                        time.sleep(WAIT_FOR_FIRST_ADD)

                        # select button
                        button = item.find_elements_by_tag_name('button')[1]

                    # add products until reached desired quantity
                    while float(item.find_element_by_xpath('div/span').text.split()[1]) < numProducts:
                        button.click()
            except Exception as e:
                print(
                    f'ERROR: Unable to add item to cart or insufficient quantity added: {product} with quantity {numProducts}')
                print(e)

    def close(self):
        super().close()

class PeaShopper(Shopper):
    def __init__(self):
        super().__init__()
        self.told_zipcode = False

    def login(self):
        self.browser.get(PEADPOD_MAIN)
        input('Please log in in browser to continue, then hit enter here (Peapod blocks automated log ins)')

        time.sleep(WAIT_FOR_PEAPOD_LOGIN)
        self.logged_in = True

    def search(self, store, _, desiredItem, itemIncludes, itemExcludes, defaultQuantity,bunchDefaultQ):
        if not self.logged_in and not self.told_zipcode:
            self.login()

        # navigate to url for item search
        url = f'https://www.peapod.com/product-search/{"%2520".join(desiredItem.name.split())}'
        self.browser.get(url)
        time.sleep(WAIT_FOR_PEAPOD_SEARCH)

        # parse out items on page
        items = self.browser.find_elements_by_class_name('product-grid-cell_price-tag')

        itemsInfo = []
        for i, item in enumerate(items):
            # find item name
            try:
                itemName = item.find_element_by_class_name('product-grid-cell_name-text').text
            except Exception as e:
                print(
                    f'Error in finding name information in store {store} for item number {i} of product search {desiredItem}')
                print(e)
                continue

            # check if out of stock
            try:
                item.find_element_by_class_name('button--add-to-cart')
            except:
                continue

            # find item price
            try:
                itemPrice = item.find_element_by_class_name('product-grid-cell_main-price').text[1:]
            except Exception as e:
                try:
                    itemPrice = item.find_element_by_class_name('product-special-grid-cell_main-price').text[1:]
                except Exception as e:
                    print(
                        f'Error in finding price information in store {store} for product {itemName} (item {i}) of product search {desiredItem}')
                    print(e)
                    continue

            # find item size
            try:
                itemSize = item.find_element_by_class_name('product-grid-cell_size').text
            except:
                itemSize = None

            # add product to list, if it's a valid product
            try:
                if re.search(itemIncludes, itemName.lower()) and (
                        not itemExcludes or not re.search(itemExcludes, itemName.lower())):
                    newProduct = PeaProduct(itemName, itemPrice, itemSize, defaultQuantity, i, desiredItem.name,None,bunchDefaultQ)
                    newProduct.totalCost(desiredItem.quantity)
                    itemsInfo.append(newProduct)
            except Exception as e:
                print(
                    f'Error creating Product Object in {store} item {i}: {itemName} with cost {itemPrice} and quantity {itemSize}')
                print(e)
                continue
        return itemsInfo

    def add_to_cart(self, store, products):
        if not self.logged_in:
            self.login()

        # add products to cart
        for product in products:
            # search product
            url = 'https://www.peapod.com/product-search/' + "%20".join(product.searchTerm.split())
            self.browser.get(url)
            time.sleep(WAIT_FOR_PEAPOD_SEARCH)

            # determine how many we want total
            numProducts = math.ceil(product.desired_quantity/product.quantity)

            try:
                # find item
                item = self.browser.find_elements_by_class_name('product-grid-cell_price-tag')[product.idx]

                if item.find_element_by_class_name('product-grid-cell_name-text').text != product.name:
                    print(f'ERROR: {product} isn\'t where it was earlier. Please add to cart manually.')
                    continue

                # add first item to cart
                item.find_element_by_class_name('button--add-to-cart').click()
                time.sleep(PEAPOD_FIRST_ADD_WAIT)

                # find field for specifying quantity
                item.find_element_by_tag_name('input').send_keys(Keys.BACKSPACE)
                item.find_element_by_tag_name('input').send_keys(str(numProducts))
                time.sleep(PEAPOD_ADD_WAIT)
                self.browser.find_element_by_id('typeahead-search-input').click()
                time.sleep(PEAPOD_ADD_UPDATE_WAIT)
            except Exception as e:
                print(
                    f'ERROR: Unable to add item to cart or insufficient quantity added: {product} with quantity {numProducts}')
                print(e)

    def zipcode(self):
    # deprecated
        # go to url for inputting zipcode
        self.browser.get('https://www.peapod.com/')
        time.sleep(PEAPOD_ZIP_WAIT)

        # find zipcode input
        self.browser.find_element_by_id('zipInput--top').send_keys(ZIPCODE)
        self.browser.find_element_by_xpath('//button[@type="submit"]').click()
        time.sleep(PEAPOD_ZIP_EXTRA_WAIT)
        try:
            self.browser.find_element_by_name('serviceLocationId').find_elements_by_tag_name('option')[1].click()
            self.browser.find_elements_by_xpath('//button[@type="submit"]')[1].click()
        except:
            pass

        time.sleep(PEAPOD_ZIP_WAIT)
        self.told_zipcode = True


    def close(self):
        super().close()

class AmazonShopper(Shopper):
    def __init__(self):
        super().__init__()
        self.told_zipcode = False

    def login(self):
        self.browser.get('https://www.amazon.com/ap/signin?openid.return_to=https%3A%2F%2Fwww.amazon.com%2Ffmc%2Fstorefront%3FalmBrandId%3DQW1hem9uIEZyZXNo%26%3FalmBrandId%3DQW1hem9uIEZyZXNo%26&suppressChangeEmailLink=1&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&suppressSignInRadioButtons=1')
        input('Please log in in browser to continue, then hit enter here (Amazon blocks automated log ins)')

        time.sleep(AMZN_LOGIN_WAIT)
        self.logged_in = True

    def search(self, store, nutrition, desiredItem, itemIncludes, itemExcludes, defaultQuantity, bunchDefaultQ):
        # log in if needed
        if not self.logged_in and not self.told_zipcode:
            if AMZN_ZIPCODE:
                self.zipcode()
            else:
                self.login()

        # go to search page
        if nutrition:
            url = f'https://www.amazon.com/s?k={"+".join(desiredItem.name)}&i=amazonfresh&rh=p_n_feature_nine_browse-bin%'+'%'.join([AMZN_NUTRITION[nut] for nut in nutrition])
        else:
            url = f'https://www.amazon.com/s?k={"+".join(desiredItem.name)}&i=amazonfresh'
        self.browser.get(url)

        # parse out items on page
        items = self.browser.find_elements_by_xpath('//div[@data-component-type="s-search-result"]')

        itemsInfo = []
        for i, item in enumerate(items):
            # find item name
            try:
                itemName = item.find_element_by_xpath('.//h2/a/span').text
            except Exception as e:
                print(
                    f'Error in finding name information in store {store} for item number {i} of product search {desiredItem}')
                print(e)
                continue

            # check if out of stock
            try:
                item.find_element_by_xpath('.//span[@aria-label="Out of Stock"]')
                continue
            except:
                pass

            # find item price
            try:
                itemPrice = item.find_element_by_xpath('.//span[@class="a-price"]').text.replace('\n','.')[1:]
            except Exception as e:
                print(
                    f'Error in finding price information in store {store} for product {itemName} (item {i}) of product search {desiredItem}')
                print(e)
                continue

            # find item size
            try:
                unitPrice = item.find_element_by_xpath('.//span[@class="a-price"]').find_elements_by_xpath('../span')[1].text[2:].split('/')
                itemSize = str(round(float(itemPrice)/float(unitPrice[0]))) + ' ' + unitPrice[1]
            except:
                print(f'Error in finding size information in store {store} for product {itemName} (item {i}) of product search {desiredItem}')
                continue

            # add product to list, if it's a valid product
            try:
                if re.search(itemIncludes, itemName.lower()) and (
                        not itemExcludes or not re.search(itemExcludes, itemName.lower())):
                    newProduct = AmazonProduct(itemName, itemPrice, itemSize, defaultQuantity, i, desiredItem.name, None,
                                            bunchDefaultQ)
                    newProduct.totalCost(desiredItem.quantity)
                    itemsInfo.append(newProduct)
            except Exception as e:
                print(
                    f'Error creating Product Object in {store} item {i}: {itemName} with cost {itemPrice} and quantity {itemSize}')
                print(e)
                continue
        return itemsInfo

    def add_to_cart(self, store, products):
        pass # TODO

    def zipcode(self):
        self.browser.find_element_by_id('nav-global-location-slot').click()
        time.sleep(AMZN_ZIPCODE_WAIT)
        self.browser.find_element_by_id('GLUXZipUpdateInput').send_keys(AMZN_ZIPCODE)
        self.browser.find_element_by_id('GLUXZipUpdate').find_element_by_tag_name('input').click()
        time.sleep(0.25)
        self.browser.find_element_by_name('glowDoneButton').click()

        self.told_zipcode = True

    def close(self):
        super().close()

# https://github.com/rambattu/cart-you-there/blob/master/find_me_slot.py
class BrowseForMe:
    def __init__(self,recover=False):
        # create shopper objects
        if any(store in STORES for store in INSTACART_STORES):
            iShopper = InstacartShopper()
        else:
            iShopper = None
        if 'peapod' in STORES:
            pShopper = PeaShopper()
        else:
            pShopper = None
        self.shoppers = {"market-basket": iShopper, "star-markets": iShopper, "wegmans": iShopper,
                         "stop-shop":iShopper,"peapod":pShopper}

        # attempt to recover previous session data, or start from scratch
        if recover:
            try:
                self.storeLists = self.load_results()
            except Exception as e:
                print('ERROR: unable to recover previous list')
                print(e)
                self.storeLists = dict()
        else:
            self.storeLists = dict()

    def load_results(self):
        return pickle.load(open('storeLists.icrt','rb'))

    def product_search(self,shoppingList):
        shoppingList = [itemRequest.split(';') for itemRequest in shoppingList]
        defaultMinCriterion = 'unit'
        save_every_x = 10
        defaultNutrition = []
        commented_out = False

        # set up store running totals
        for store in STORES:
            if not store in self.storeLists:
                self.storeLists[store] = dict()

                # running total of shopping lists
                self.storeLists[store]['total'] = 0
                self.storeLists[store]['adjusted_total'] = 0
                self.storeLists[store]['missingItems'] = []

        # check each desired item
        for j, itemRequest in enumerate(shoppingList):
            # lines that we skip
            if not itemRequest:
                continue
            if itemRequest[0] == '###':
                commented_out = not commented_out
            if commented_out or itemRequest[0][0] == '#':
                continue

            # options line (Options;unit/net
            if itemRequest[0].lower() == 'options':
                # net vs unit price
                if len(itemRequest) > 1:
                    if itemRequest[1].lower() == 'net':
                        defaultMinCriterion = 'net'
                    elif itemRequest[1].lower() == 'unit':
                        defaultMinCriterion = 'unit'
                    else:
                        print(f'ERROR: Unable to parse default criterion for minimum price. Using default: {defaultMinCriterion}')
                # instacart's nutrition options
                if len(itemRequest) > 2:
                    nutrition = itemRequest[2].split(',')
                    if all([nut in NUTRITION_OPTIONS for nut in nutrition]):
                        defaultNutrition = nutrition
                    else:
                        print('ERROR: Invalid default nutrition parameters')
                continue
            minCriterion = defaultMinCriterion
            nutrition = defaultNutrition

            # parse item name/quantity
            try:
                desiredItem = Product(itemRequest[0], '1.0', itemRequest[1], 1.0, None,None)
            except Exception as e:
                print(f'ERROR in line {j}: unable to parse item name/quantity')
                print(e)
                continue

            # parse terms that item name must include
            try:
                itemIncludes = '|'.join([item.lower().strip('\n') for item in itemRequest[2].split(' OR ')])
            except Exception as e:
                print(f'ERROR in line {j}: unable to parse item words to look for')
                print(e)
                continue

            # parse terms that item name must exclude
            if len(itemRequest) > 3 and itemRequest[3]:
                try:
                    itemExcludes = '|'.join([item.lower().strip('\n') for item in itemRequest[3].split(' OR ')])
                except Exception as e:
                    print(f'ERROR in line {j}: unable to parse item words to avoid')
                    print(e)
                    continue
            else:
                itemExcludes = None

            # parse default quantity and bunch default quantity
            if len(itemRequest) > 4 and itemRequest[4]:
                defaults = itemRequest[4].split(',')
                try:
                    defaultQuantity = Product.quantify(defaults[0],None,None,None)
                    if len(defaults) > 1:
                        bunchDefaultQuantity = Product.quantify(defaults[1],None,None,None)
                    else:
                        bunchDefaultQuantity = None
                except Exception as e:
                    print(f'ERROR in line {j}: unable to parse default quantity')
                    print(e)
                    continue
            else:
                defaultQuantity = 1.0
                bunchDefaultQuantity = None

            # parse whether to use net cost or unit cost
            if len(itemRequest) > 5 and itemRequest[5] == 'net':
                minCriterion = 'net'
            elif len(itemRequest) > 5 and itemRequest[5] == 'unit':
                minCriterion = 'unit'
            elif len(itemRequest) > 5 and itemRequest[5]:
                print(f'ERROR in line {j}: unable to parse whether to use net or unit price. Using default: {defaultMinCriterion}')

            # parse nutrition features to use
            if len(itemRequest) > 6:
                if not itemRequest[6]:
                    nutrition = []
                else:
                    nutrition = itemRequest[6].split(',')
                    if not all([nut in NUTRITION_OPTIONS for nut in nutrition]):
                        print(f'ERROR in line {j}: Invalid nutrition parameters')
                        nutrition = defaultNutrition

            # check stores for items
            for store in STORES:
                # if item already in store, subtract it from total, then remove from shopping list
                if desiredItem.name in self.storeLists[store]['missingItems']:
                    self.storeLists[store]['missingItems'].remove(desiredItem.name)
                if desiredItem.name in self.storeLists[store]:
                    if self.storeLists[store][desiredItem.name]:
                        self.storeLists[store]['total'] -= self.storeLists[store][desiredItem.name].total
                    del self.storeLists[store][desiredItem.name]

                # perform product search
                try:
                    itemsInfo = self.shoppers[store].search(store,nutrition,desiredItem,itemIncludes,itemExcludes,defaultQuantity,bunchDefaultQuantity)
                except Exception as e:
                    print(f'ERROR: Unable to shop store {store} for item {desiredItem}.')
                    print(e)
                    continue

                # find best deal and add to store's dict
                if len(itemsInfo) > 0:
                    cheapestItem = min(itemsInfo, key=lambda item: item.total if minCriterion == 'net' else item.unit_price)
                    self.storeLists[store]['total'] += cheapestItem.total
                else:
                    cheapestItem = None
                    self.storeLists[store]['missingItems'].append(desiredItem.name)
                self.storeLists[store][desiredItem.name] = cheapestItem

            # save every x items
            if (j+1) % save_every_x == 0:
                self.save_results()
        # save at end
        self.save_results()

    def analyze(self):
        # generate list of products
        products = [product for product in self.storeLists[STORES[0]] if isinstance(self.storeLists[STORES[0]][product],Product) or self.storeLists[STORES[0]][product] is None]

        # save product info to file
        with open('shopping_lists.csv','w+') as csvfile:
            prodWriter = csv.writer(csvfile)
            # column headers
            prodWriter.writerow(['Product']+[store_term for store in STORES for store_term in (str(store) + ' product name','net price (unit price)')])

            # write each product's info
            for product in products:
                costs_and_names = []
                for store in STORES:
                    if self.storeLists[store][product]:
                        costs_and_names.append(self.storeLists[store][product].name)
                        costs_and_names.append(f'{"{:.2f}".format(self.storeLists[store][product].total)} '
                                               f'({self.storeLists[store][product].originalPrice}'
                                               f'{" / " + self.storeLists[store][product].originalQuantity if self.storeLists[store][product].originalQuantity else ""})')
                    else:
                        costs_and_names.extend(['Unavailable','Unavailable'])
                prodWriter.writerow([product] + costs_and_names)

            # write totals
            prodWriter.writerow(['Totals'] + [store_term for store in STORES for store_term in
                                               ('Total:', "{:.2f}".format(self.storeLists[store]['total']))])

            # calculate adjusted totals, averaging the price from other stores with the product if this store didn't have it
            totals = [self.storeLists[store]['total'] for store in STORES]
            for i, currentStore in enumerate(STORES):
                for product in self.storeLists[currentStore]['missingItems']:
                    finds = 0
                    total = 0
                    for otherStore in STORES:
                        if self.storeLists[otherStore][product]:
                            total += self.storeLists[otherStore][product].total
                            finds += 1
                    if finds:
                        totals[i] += total/finds

            # write adjusted totals
            prodWriter.writerow(['Normalized Totals'] + [store_term for total in totals for store_term in
                                              ('Total:', "{:.2f}".format(total))])

        with open('missing.csv','w+') as csvfile:
            prodWriter = csv.writer(csvfile)
            # column headers
            prodWriter.writerow(STORES)
            for product in products:
                missing = [self.storeLists[store][product] is None for store in STORES]
                if any(missing):
                    prodWriter.writerow([product if missing[i] else '' for i in range(len(missing))])

    def add_to_cart(self,store):
        # get list of products
        if store not in STORES:
            print('ERROR: Invalid Store')
            return
        products = [self.storeLists[store][product] for product in self.storeLists[store] if isinstance(self.storeLists[STORES[0]][product],Product)]

        # add products to cart
        self.shoppers[store].add_to_cart(store,products)

    def save_results(self):
        with open('storeLists.icrt','wb+') as outfile:
            pickle.dump(self.storeLists,outfile)

    def close_and_quit(self):
        # close all shoppers
        for shopper in self.shoppers:
            if self.shoppers[shopper]:
                self.shoppers[shopper].close()

    def remove_products(self,store_to_remove,product_name):
        # completely delete product
        if store_to_remove == 'all':
            success = False
            for store in STORES:
                try:
                    del self.storeLists[store][product_name]
                    success = True
                except:
                    continue
            return success
        # remove product from single store
        else:
            if not store_to_remove in STORES:
                print('ERROR: Invalid Store')
                return True
            try:
                self.storeLists[store_to_remove][product_name] = None
                return True
            except:
                return False

if __name__ == '__main__':
    action = None
    driver = None
    while action != 'quit' and action != '7':
        # prompt user for action
        action = input('What would you like to do?\nOptions:\n[1] recover\n[2] shop\n[3] remove\n[4] analyze\n[5] add to cart\n[6] save results\n[7] quit\n')

        # perform action
        if action == 'recover' or action == '1':
            driver = BrowseForMe(recover=True)
        elif action == 'shop' or action == '2':
            # get shopping list
            shoppingList = [item.strip('\n') for item in open(SHOPPINGLISTFILE,'r').readlines()]

            # create driver if needed; log in if needed
            if not driver:
                driver = BrowseForMe()

            # shop!
            driver.product_search(shoppingList)
        elif action == 'remove' or action == '3':
            # ensure we have a shopping cart
            if not driver:
                print('ERROR: No shopping to remove')
                continue

            # prompt for what to remove and from where
            product = input('What product would you like to remove? (Give the full product name)')
            # prompt for store name
            store = input('\n'.join(['What store?\nOptions:']+['['+str(i)+'] ' + STORES[i] for i in range(len([STORES]))])+f'\n[{len([STORES])}] all\n')

            # parse number if given
            try:
                if int(store) == len(STORES):
                    store = 'all'
                else:
                    store = STORES[int(store)]
            except:
                pass

            # remove product
            success = driver.remove_products(store,product)
            if not success:
                print('ERROR: Unable to find product in store(s).')
        elif action == 'analyze' or action == '4':
            # ensure we have a shopping cart
            if not driver:
                print('ERROR: No shopping to analyze')
                continue

            #analyze shopping cart
            driver.analyze()
        elif action == 'add to cart' or action == '5':
            # ensure we have a shopping cart
            if not driver:
                print('ERROR: No shopping to add')
                continue

            # prompt for store name
            store = input('\n'.join(['What store?\nOptions:']+['['+str(i)+'] ' + STORES[i] for i in range(len(STORES))])+'\n')

            # parse number if given
            try:
                store = STORES[int(store)]
            except:
                pass

            # add items to cart
            driver.add_to_cart(store)
        elif action == 'save results' or action == '6':
            # ensure we have results to save
            if not driver:
                print('ERROR: No results to save')
                continue
            # save results
            driver.save_results()
    if driver:
        driver.save_results()
        driver.close_and_quit()