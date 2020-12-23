# Finding the dream apartment with Python
## Scraping Finn.no for listings
Recently, my partner and I had to find a new apartment, and we decided to buy one instead of renting one. However, finding the "dream" apartment is no easy task. Searching for listings in Oslo took much of our time, and we seldomly found one that ticked all boxes. The commute time was especially frustrating since we had to find it manually for each listing! Therefore, we decided to automate the apartment hunt. We made a script to scrape [Finn.no](https://finn.no), Norway's largest apartment listing webpage, and store the results in a local SQL database. Here is a short writeup of our development process.

Early on, we realised that we needed to use [Selenium](https://www.selenium.dev/). Finn generates the search result pages with JavaScript, so we couldn't merely parse the HTML for links. Instead, we used Selenium to control a chrome window and get the links for all apartment listings that matched a search query. 

Once we had a list of all apartments from the search results page (so all local apartments for sale), we used the [Requests](https://requests.readthedocs.io/en/master/) library to download the HTML for all these pages and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) to navigate the HTML and extract the relevant information.

To find the relevant HTML blocks for our scraper, we used the developer tools in Firefox. If you press the button left of the "Inspector" tab, you can select parts of the webpage and see its HTML tag.  

The next step was to find the commute time for each apartment. To find these commute times, we first needed the apartment coordinates. Luckily, the Norwegian public transport company, [EnTur](https://entur.no/) has a public [GeoCoder API](https://developer.entur.org/pages-geocoder-api) which we can use for this task. Using it is as easy as a single GET request with an identifying header and requires no registration beforehand.

Once we had the coordinates, we wanted the commute time to OsloMet and the University of Oslo. We walk, bike and take public transport to work, so those were the relevant times to find. Luckily, EnTur also has a free [JourneyPlanner API](https://developer.entur.org/pages-journeyplanner-journeyplanner-v2), which we can use to get walk distances and how long it takes to travel with different means of transport! The JourneyPlanner is a GraphQL API with an [easy-to-use editor](https://api.entur.io/journey-planner/v2/ide/) to explore the API and find the exact message to send with the POST requests.

After collecting the relevant information from each apartment listing and the commute times, we saved it in a dictionary. So we had a list of dictionaries, with one dictionary per listing. The next step was to store this information in a database so that we could inspect it without spamming Finn.no with HTTP requests. We decided to use an SQLite database, which we created with the builtin [sqlite3](https://docs.python.org/3/library/sqlite3.html) module. To populate the database, we converted the list of dictionaries to a [Pandas](https://pandas.pydata.org/) DataFrame and used the `to_sql` method.

## Finding interesting listings with SQL
With the SQLite database ready, we wanted to explore it to find appealing apartments. With some short SQL queries, we could discover apartments within our budget, examine which apartments are cheapest per square meter, and explore which apartments have the best commute.
We wanted the output in the terminal window, so we used [Rich](https://github.com/willmcgugan/rich) to generate pretty tables with formatted text describing their contents. Below, we have some example queries we ran and the corresponding output.

Note, that Finn updates their webpages often and if you want to try something similar for yourself, you might have to update the scraping section of the code to fit how the webpages are structured currently. 

<pre>                                                 <u style="text-decoration-style:single"><b>The 10 cheapest apartments:</b></u>                                                 
 Query: 
<i>    SELECT </i><font color="#4E9A06"><i>&quot;adresse&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;felleskost/mnd.&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;totalpris&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;primærrom&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;bruksareal&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;sykkeltid-uio&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;sykkeltid-met&quot;</i></font><i> </i>
<i>    FROM boligdata </i>
<i>    WHERE totalpris is not NULL </i>
<i>    AND bruksareal &gt;= </i><font color="#729FCF"><i><b>20</b></i></font>
<i>    ORDER BY totalpris </i>
<i>    LIMIT </i><font color="#729FCF"><i><b>5</b></i></font>
<i>    </i> 
 Result:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃<b> adresse                            </b>┃<b> felleskost/mnd. </b>┃<b> totalpris </b>┃<b> primærrom </b>┃<b> bruksareal </b>┃<b> sykkeltid-uio </b>┃<b> sykkeltid-met </b>┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Øvrefoss 6H, 0555 Oslo             │ 8044            │ 3173248   │ 38.0      │ 57.0       │ 20            │ 11            │
│ Middelthuns gate 11B, 0368 Oslo    │ 2926            │ 3566090   │ 50.0      │ 50.0       │ 12            │ 6             │
│ Jolly Kramer-Johansens gate 2,     │ 2892            │ 4193312   │ 39.0      │ 39.0       │ 20            │ 18            │
│ 0475 Oslo                          │                 │           │           │            │               │               │
│ Sporveisgata 8A, 0354 Oslo         │ 4613            │ 5134207   │ 88.0      │ 99.0       │ 13            │ 2             │
│ Lørenveien 65, 0585 Oslo           │ 1990            │ 5237142   │ 53.0      │ 53.0       │ 28            │ 24            │
└────────────────────────────────────┴─────────────────┴───────────┴───────────┴────────────┴───────────────┴───────────────┘
However, just because an apartment is cheap in total does not mean the price per square meter is good.

                                    <u style="text-decoration-style:single"><b>The 10 cheapest aparment (per m^2) within price range</b></u>                                    
 Query: 
<i>    SELECT totalpris/bruksareal as kvadratmeterpris, </i>
<font color="#4E9A06"><i>&quot;adresse&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;felleskost/mnd.&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;totalpris&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;primærrom&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;bruksareal&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;sykkeltid-uio&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;sykkeltid-met&quot;</i></font><i> </i>
<i>    FROM boligdata </i>
<i>    WHERE totalpris is not NULL </i>
<i>    AND totalpris &lt;= </i><font color="#729FCF"><i><b>4000000</b></i></font>
<i>    ORDER BY kvadratmeterpris </i>
<i>    LIMIT </i><font color="#729FCF"><i><b>5</b></i></font>
<i>    </i> 
 Result:
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃<b> kvadratmeterpris </b>┃<b> adresse         </b>┃<b> felleskost/mnd. </b>┃<b> totalpris </b>┃<b> primærrom </b>┃<b> bruksareal </b>┃<b> sykkeltid-uio </b>┃<b> sykkeltid-met </b>┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ 55671.017543859… │ Øvrefoss 6H,    │ 8044            │ 3173248   │ 38.0      │ 57.0       │ 20            │ 11            │
│                  │ 0555 Oslo       │                 │           │           │            │               │               │
│ 71321.8          │ Middelthuns     │ 2926            │ 3566090   │ 50.0      │ 50.0       │ 12            │ 6             │
│                  │ gate 11B, 0368  │                 │           │           │            │               │               │
│                  │ Oslo            │                 │           │           │            │               │               │
│ 147458.11111111… │ Dalsbergstien   │ 5317            │ 2654246   │ 20.0      │ 18.0       │ 14            │ 1             │
│                  │ 3, 0170 Oslo,   │                 │           │           │            │               │               │
│                  │ 0170 Oslo       │                 │           │           │            │               │               │
└──────────────────┴─────────────────┴─────────────────┴───────────┴───────────┴────────────┴───────────────┴───────────────┘
We are also interested in apartments with a balcony.

                                          <u style="text-decoration-style:single"><b>The 10 cheapest apartments with a balcony</b></u>                                          
 Query: 
<i>    SELECT </i><font color="#4E9A06"><i>&quot;adresse&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;felleskost/mnd.&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;totalpris&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;primærrom&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;bruksareal&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;sykkeltid-uio&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;sykkeltid-met&quot;</i></font><i> </i>
<i>    FROM boligdata</i>
<i>    WHERE totalpris is not NULL </i>
<i>    AND primærrom &lt; bruksareal</i>
<i>    ORDER BY totalpris </i>
<i>    LIMIT </i><font color="#729FCF"><i><b>10</b></i></font>
<i>    </i> 
 Result:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃<b> adresse                            </b>┃<b> felleskost/mnd. </b>┃<b> totalpris </b>┃<b> primærrom </b>┃<b> bruksareal </b>┃<b> sykkeltid-uio </b>┃<b> sykkeltid-met </b>┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Øvrefoss 6H, 0555 Oslo             │ 8044            │ 3173248   │ 38.0      │ 57.0       │ 20            │ 11            │
│ Sporveisgata 8A, 0354 Oslo         │ 4613            │ 5134207   │ 88.0      │ 99.0       │ 13            │ 2             │
│ Hans Nielsen Hauges plass 1, 0481  │ 3942            │ 5400292   │ 80.0      │ 83.0       │ 19            │ 13            │
│ Oslo                               │                 │           │           │            │               │               │
│ Nordre gate 22A, 0551 Oslo         │ 1980            │ 5433756   │ 40.0      │ 45.0       │ 25            │ 12            │
│ Camilla Colletts vei 15, 0258 Oslo │ 7484            │ 6174905   │ 103.0     │ 108.0      │ 16            │ 3             │
│ Nordre gate 22 A, 0551 Oslo        │ 3760            │ 8195116   │ 82.0      │ 86.0       │ 25            │ 12            │
│ Nordre gate 22 A, 0551 Oslo        │ 3760            │ 8345116   │ 82.0      │ 86.0       │ 25            │ 12            │
│ Ensjøveien 34, 0661 Oslo           │ 3785            │ 9307706   │ 91.0      │ 94.0       │ 35            │ 22            │
│ Rostockgata 54, 0194 Oslo          │ 2705            │ 9533756   │ 65.0      │ 70.0       │ 30            │ 14            │
│ Doktor Holms vei 17D, 0787 Oslo    │ 4778            │ 10463742  │ 134.0     │ 142.0      │ 18            │ 25            │
└────────────────────────────────────┴─────────────────┴───────────┴───────────┴────────────┴───────────────┴───────────────┘
And a short commute

                        <u style="text-decoration-style:single"><b>The 10 cheapest apartments with a commute &lt;20 minutes to both UiO and OsloMet</b></u>                        
 Query: 

<i>    SELECT </i><font color="#4E9A06"><i>&quot;adresse&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;felleskost/mnd.&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;totalpris&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;primærrom&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;bruksareal&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;sykkeltid-uio&quot;</i></font><i>,</i><font color="#4E9A06"><i>&quot;sykkeltid-met&quot;</i></font><i>, </i>
<font color="#4E9A06"><i>&quot;kollektivtid-uio&quot;</i></font><i>, </i><font color="#4E9A06"><i>&quot;kollektivtid-met&quot;</i></font>
<i>    FROM boligdata</i>
<i>    WHERE totalpris is not NULL </i>
<i>    AND </i><font color="#4E9A06"><i>&quot;sykkeltid-uio&quot;</i></font><i> &lt; </i><font color="#729FCF"><i><b>20</b></i></font>
<i>    AND </i><font color="#4E9A06"><i>&quot;sykkeltid-met&quot;</i></font><i> &lt; </i><font color="#729FCF"><i><b>20</b></i></font>
<i>    AND </i><font color="#4E9A06"><i>&quot;kollektivtid-uio&quot;</i></font><i> &lt; </i><font color="#729FCF"><i><b>30</b></i></font>
<i>    AND </i><font color="#4E9A06"><i>&quot;kollektivtid-met&quot;</i></font><i> &lt; </i><font color="#729FCF"><i><b>30</b></i></font>
<i>    ORDER BY totalpris </i>
<i>    LIMIT </i><font color="#729FCF"><i><b>10</b></i></font>
<i>    </i> 
 Result:
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃<b> adresse     </b>┃<b> felleskost/… </b>┃<b> totalpris </b>┃<b> primærrom </b>┃<b> bruksareal </b>┃<b> sykkeltid-… </b>┃<b> sykkeltid-m… </b>┃<b> kollektivt… </b>┃<b> kollektivti… </b>┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Dalsbergst… │ 5317         │ 2654246   │ 20.0      │ 18.0       │ 14          │ 1            │ 18          │ 5            │
│ 3, 0170     │              │           │           │            │             │              │             │              │
│ Oslo, 0170  │              │           │           │            │             │              │             │              │
│ Oslo        │              │           │           │            │             │              │             │              │
│ Middelthuns │ 2926         │ 3566090   │ 50.0      │ 50.0       │ 12          │ 6            │ 19          │ 16           │
│ gate 11B,   │              │           │           │            │             │              │             │              │
│ 0368 Oslo   │              │           │           │            │             │              │             │              │
│ Sporveisga… │ 4613         │ 5134207   │ 88.0      │ 99.0       │ 13          │ 2            │ 16          │ 8            │
│ 8A, 0354    │              │           │           │            │             │              │             │              │
│ Oslo        │              │           │           │            │             │              │             │              │
│ Geitmyrsve… │ 3595         │ 5305392   │ 55.0      │ 55.0       │ 11          │ 6            │ 19          │ 15           │
│ 73B, 0455   │              │           │           │            │             │              │             │              │
│ Oslo        │              │           │           │            │             │              │             │              │
│ Camilla     │ 7484         │ 6174905   │ 103.0     │ 108.0      │ 16          │ 3            │ 19          │ 7            │
│ Colletts    │              │           │           │            │             │              │             │              │
│ vei 15,     │              │           │           │            │             │              │             │              │
│ 0258 Oslo   │              │           │           │            │             │              │             │              │
│ Bogstadvei… │ 2026         │ 6538913   │ 64.0      │ 64.0       │ 11          │ 6            │ 15          │ 12           │
│ 62C, 0366   │              │           │           │            │             │              │             │              │
│ Oslo        │              │           │           │            │             │              │             │              │
│ Ullevålsve… │ 4675         │ 7117248   │ 95.0      │ 95.0       │ 8           │ 5            │ 12          │ 8            │
│ 81, 0454    │              │           │           │            │             │              │             │              │
│ Oslo        │              │           │           │            │             │              │             │              │
│ Waldemar    │ 2751         │ 7769912   │ 73.0      │ 73.0       │ 18          │ 5            │ 22          │ 10           │
│ Thranes     │              │           │           │            │             │              │             │              │
│ gate 61,    │              │           │           │            │             │              │             │              │
│ 0173 Oslo   │              │           │           │            │             │              │             │              │
│ Benneches   │ 2860         │ 9444000   │ 110.0     │ 110.0      │ 14          │ 1            │ 19          │ 6            │
│ gate 1,     │              │           │           │            │             │              │             │              │
│ 0169 Oslo   │              │           │           │            │             │              │             │              │
│ Ole Vigs    │ 5048         │ 13000940  │ 99.0      │ 102.0      │ 10          │ 5            │ 16          │ 14           │
│ gate 24D,   │              │           │           │            │             │              │             │              │
│ 0366 Oslo   │              │           │           │            │             │              │             │              │
└─────────────┴──────────────┴───────────┴───────────┴────────────┴─────────────┴──────────────┴─────────────┴──────────────┘

                                             <u style="text-decoration-style:single"><b>Information about each postal zone</b></u>                                              
 Query: 

<i>    SELECT</i>
<i>     postnummer,</i>
<i>     AVG</i><i><b>(</b></i><i>totalpris/bruksareal</i><i><b>)</b></i><i>,</i>
<i>     AVG</i><i><b>(</b></i><i>totalpris</i><i><b>)</b></i><i>,</i>
<i>     AVG</i><i><b>(</b></i><i>bruksareal</i><i><b>)</b></i><i>,</i>
<i>     COUNT</i><i><b>(</b></i><i>totalpris</i><i><b>)</b></i>
<i>    FROM boligdata </i>
<i>    WHERE totalpris IS NOT NULL</i>
<i>    GROUP BY postnummer</i>
<i>    ORDER BY avg</i><i><b>(</b></i><i>totalpris/bruksareal</i><i><b>)</b></i><i> DESC</i>
<i>    </i> 
 Result:
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃<b> postnummer </b>┃<b> AVG(totalpris/bruksareal) </b>┃<b> AVG(totalpris)     </b>┃<b> AVG(bruksareal)    </b>┃<b> COUNT(totalpris) </b>┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 0286       │ 207172.20547945207        │ 30247142.0         │ 146.0              │ 1                │
│ 0252       │ 163264.66615766368        │ 21487687.5         │ 115.5              │ 2                │
│ 0170       │ 147458.11111111112        │ 2654246.0          │ 18.0               │ 1                │
│ 0194       │ 131527.16616541354        │ 13244277.333333334 │ 101.33333333333333 │ 3                │
│ 0366       │ 128130.34361745584        │ 11362441.0         │ 86.66666666666667  │ 3                │
│ 0266       │ 125069.2                  │ 13132266.0         │ 105.0              │ 1                │
│ 0272       │ 117615.5980427582         │ 33383232.0         │ 245.5              │ 2                │
│ 0475       │ 107520.82051282052        │ 4193312.0          │ 39.0               │ 1                │
│ 0173       │ 106437.1506849315         │ 7769912.0          │ 73.0               │ 1                │
│ 0551       │ 104359.47080103359        │ 7324662.666666667  │ 72.33333333333333  │ 3                │
│ 0661       │ 99018.14893617021         │ 9307706.0          │ 94.0               │ 1                │
│ 0585       │ 98814.0                   │ 5237142.0          │ 53.0               │ 1                │
│ 0455       │ 96461.67272727273         │ 5305392.0          │ 55.0               │ 1                │
│ 0169       │ 85854.54545454546         │ 9444000.0          │ 110.0              │ 1                │
│ 0655       │ 83607.86686838124         │ 11052960.0         │ 132.2              │ 1                │
│ 0575       │ 80747.4629959082          │ 6051553.5          │ 75.0               │ 2                │
│ 0265       │ 76213.23799427724         │ 18420403.0         │ 245.5              │ 2                │
│ 0454       │ 74918.4                   │ 7117248.0          │ 95.0               │ 1                │
│ 0787       │ 73688.32394366198         │ 10463742.0         │ 142.0              │ 1                │
│ 0368       │ 71321.8                   │ 3566090.0          │ 50.0               │ 1                │
│ 0481       │ 65063.75903614458         │ 5400292.0          │ 83.0               │ 1                │
│ 0183       │ 62773.27906976744         │ 10797004.0         │ 172.0              │ 1                │
│ 0566       │ 59596.637209302324        │ 25626554.0         │ 430.0              │ 1                │
│ 0258       │ 57175.0462962963          │ 6174905.0          │ 108.0              │ 1                │
│ 0555       │ 55671.01754385965         │ 3173248.0          │ 57.0               │ 1                │
│ 0354       │ 51860.67676767677         │ 5134207.0          │ 99.0               │ 1                │
└────────────┴───────────────────────────┴────────────────────┴────────────────────┴──────────────────┘
</pre>