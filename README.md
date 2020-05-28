# groceries
This program implements price comparison across multiple grocery services using Selenium webscraping. With it, you can

## Setting up
Install all needed packages and download the chromedriver for Selenium. Place that chromedriver in 'venv/bin' or change the `CHROMEDRIVER`
file path listed at the top of instacart.py to the correct location.

Each time you start a new session, export your instacart username and password on the command line.

To change which stores are being checked, edit the "STORES" variable in instacart.py.

## Running
Edit shopping_list.txt to contain your shopping list (see below). 

`python3 groceries.m`

You may start by hitting 'shop'. That will take a while, depending on the size of your shopping list. (Note that for peapod, you must sign
in manually, since peapod blocks automated sign in attempts. You will then hit Enter in the command line once you've logged in.)

After that, you'll want to 'analyze' the results to view the cost from each store. You can view the results in shopping_lists.csv.

You may then want to 'recheck' some of the products with slightly different terms, or add new ones. To do so, simply edit shopping_list.txt
and rerun the shop selection (no need to close the program).

If you do not want to re-search a product, but just want to remove it (from one store, or all of them), you may do so with remove.

If you closed the program, or it crashed accidentally (it autosaves every 10 products searched and at the end of a search), 
you can reload what you have shopped so far.

You may manually save your cart with 'save results'.

Once you have approved all items found by the shopper, you may add them to you cart with 'add to cart'.

When done, select 'quit' to close the browser and end the program.

## instacart.py
This is the backbone of the program. It implements a "Product" class that contains relevant necessary information, as well as
an abstract "Shopper" class for each store that is being compared

## shopping_list.txt
This is the file that contains your shopping list. The shopping list must be in the following format. Note the semicolons and commas.
Many examples can be found in shopping_list.txt:

search term;quantity;valid possibility 1 OR valid possibility 2;invalid possibility 1 OR invalid possibility 2;
default weight,default bunch weight;nutrition option 1,nutrition option 2

**search term**: The term that will be typed in the search bar. This must be unique for each item, as 
it is used that the key when storing information about the search.

**quantity**: The amount of the item that you want (typically weight). This can be parsed from a number of different units (see the Product class 
quantify method for full details on what units can be parsed as of now). Warning: you almost always want this to be weight. You may be tempted
to do it based on just a number instead. Most likely, don't. What does it mean to have 5 carrots, when carrots are purchased per pound?
Reserve any non-weight quantities for items that cannot be measured by weight (bowls, for example).

**valid possibility 1 OR valid possibility 2**: For each product result in a search, the program will check whether the product's name fits
this search term. You can specify multiple valid product name terms using the 'OR' keyword between each one. The program will check whether
any of those terms are present in the product name, to determine whether it is a match for the product you are searching for. Regex may be
used here as well. One particularly useful regex allows you to check whether all of the keywords appear in the name *anywhere* (regardless 
of order): `(?=.*word1)(?=.*word2)(?=.*word3)`. See many examples in this file.

**invalid possibility 1 OR invalid possibility 2**: Same as previous, except we make sure the product name does *not* include it.

**default weight**: Many products are listed not by weight, but by quantity. In such a case, the program will use the default weight listed here.
If you do not give a weight, it will default to 1.0. **IMPORTANT**: Pretty much all produce needs a default weight, since any given item is
often sold both per pound and per item. If you do not give a default weight, the program may think that the product is a much worse deal
than it actually is.

**default bunch weight**: Some products are also sold by the bunch (bananas, for example). In this case, give a default bunch weight.
If you don't the program will give you a warning and skip the item, potentially making you miss a good deal.

**nutrition option 1,nutrition option 2**: Instacart allows certain nutrition filters. Options are: 
vegan, kosher, is_organic, fat_free, gluten_free, and sugar_free. You may choose as many filters as desired by sepearating each by commas.
While peapod also allows filtering, it blocks automated attempts at doing so. Therefore, at least for now, peapod searches ignore these options.

You may comment out individual products by typing a single `#` at the beginning of a line. You may comment out a block of lines 
by making a line with just the characters `###`. To end a comment, make another such line.

## Adding stores
To add another store, create the appropriate product and shopper classes, add the store in STORES, and update the BrowseForMe `__init__`.

## Acknowledgements
My gratitude to @rambattu for the Instacart login: https://github.com/rambattu/cart-you-there/blob/master/find_me_slot.py
