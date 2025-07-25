--------------------------------------------------
Table full name: countries
Columns:
  - country_id (INTEGER)
  - country_iso_code (CHAR(2))
  - country_name (TEXT)
  - country_subregion (TEXT)
  - country_subregion_id (INTEGER)
  - country_region (TEXT)
  - country_region_id (INTEGER)
  - country_total (TEXT)
  - country_total_id (INTEGER)
Sample rows:
  [(52769, 'SG', 'Singapore', 'Asia', 52793, 'Asia', 52802, 'World total', 52806),
   (52770, 'IT', 'Italy', 'Western Europe', 52799, 'Europe', 52803, 'World total', 52806),
   (52771, 'CN', 'China', 'Asia', 52793, 'Asia', 52802, 'World total', 52806)]
--------------------------------------------------
Table full name: customers
Columns:
  - cust_id (INTEGER)
  - cust_first_name (TEXT)
  - cust_last_name (TEXT)
  - cust_gender (CHAR(1))
  - cust_year_of_birth (INTEGER)
  - cust_marital_status (TEXT)
  - cust_street_address (TEXT)
  - cust_postal_code (TEXT)
  - cust_city (TEXT)
  - cust_city_id (INTEGER)
  - cust_state_province (TEXT)
  - cust_state_province_id (INTEGER)
  - country_id (INTEGER)
  - cust_main_phone_number (TEXT)
  - cust_income_level (TEXT)
  - cust_credit_limit (REAL)
  - cust_email (TEXT)
  - cust_total (TEXT)
  - cust_total_id (INTEGER)
  - cust_src_id (INTEGER)
  - cust_eff_from (DATE)
  - cust_eff_to (DATE)
  - cust_valid (CHAR(1))
Sample rows:
  [(1, 'Abigail', 'Kessel', 'M', 1957, None, '7 South 3rd Circle', '30828', 'Downham Market', 51396, 'England - Norfolk', 52591, 52789, '127-379-8954', 'G: 130,000 - 149,999', 9000.0, 'Kessel@company.example.com', 'Customer total', 52772, None, '2019-01-01', None, 'I'),
   (2, 'Anne', 'Koch', 'F', 1968, None, '7 South Airway Circle', '86319', 'Salamanca', 52286, 'Salamanca', 52733, 52778, '680-327-1419', 'I: 170,000 - 189,999', 10000.0, 'Koch@company.example.com', 'Customer total', 52772, None, '2019-01-01', None, 'A')]
--------------------------------------------------
Table full name: promotions
Columns:
  - promo_id (INTEGER)
  - promo_name (TEXT)
  - promo_subcategory (TEXT)
  - promo_subcategory_id (INTEGER)
  - promo_category (TEXT)
  - promo_category_id (INTEGER)
  - promo_cost (REAL)
  - promo_begin_date (DATE)
  - promo_end_date (DATE)
  - promo_total (TEXT)
  - promo_total_id (INTEGER)
Sample rows:
  [(33, 'post promotion #20-33', 'downtown billboard', 20, 'post', 9, 77200.0, '2019-09-15', '2019-11-15', 'Promotion total', 1),
   (34, 'newspaper promotion #19-34', 'coupon news', 19, 'newspaper', 8, 22400.0, '2019-07-16', '2019-09-16', 'Promotion total', 1)]
--------------------------------------------------
Table full name: products
Columns:
  - prod_id (INTEGER)
  - prod_name (TEXT)
  - prod_desc (TEXT)
  - prod_subcategory (TEXT)
  - prod_subcategory_id (INTEGER)
  - prod_subcategory_desc (TEXT)
  - prod_category (TEXT)
  - prod_category_id (INTEGER)
  - prod_category_desc (TEXT)
  - prod_weight_class (INTEGER)
  - prod_unit_of_measure (TEXT)
  - prod_pack_size (TEXT)
  - supplier_id (INTEGER)
  - prod_status (TEXT)
  - prod_list_price (REAL)
  - prod_min_price (REAL)
  - prod_total (TEXT)
  - prod_total_id (INTEGER)
  - prod_src_id (INTEGER)
  - prod_eff_from (DATE)
  - prod_eff_to (DATE)
  - prod_valid (CHAR(1))
Sample rows:
  [(14, 'Pitching Machine and Batting Cage Combo', ..., 'A'),
   (19, 'Cricket Bat Bag', ..., 'A')]
--------------------------------------------------
Table full name: times
Columns:
  - time_id (DATE)
  - day_name (TEXT)
  - day_number_in_week (INTEGER)
  - day_number_in_month (INTEGER)
  - calendar_week_number (INTEGER)
  - fiscal_week_number (INTEGER)
  - week_ending_day (DATE)
  - week_ending_day_id (INTEGER)
  - calendar_month_number (INTEGER)
  - fiscal_month_number (INTEGER)
  - calendar_month_desc (TEXT)
  - calendar_month_id (INTEGER)
  - fiscal_month_desc (TEXT)
  - fiscal_month_id (INTEGER)
  - days_in_cal_month (INTEGER)
  - days_in_fis_month (INTEGER)
  - end_of_cal_month (DATE)
  - end_of_fis_month (DATE)
  - calendar_month_name (TEXT)
  - fiscal_month_name (TEXT)
  - calendar_quarter_desc (CHAR(7))
  - calendar_quarter_id (INTEGER)
  - fiscal_quarter_desc (CHAR(7))
  - fiscal_quarter_id (INTEGER)
  - days_in_cal_quarter (INTEGER)
  - days_in_fis_quarter (INTEGER)
  - end_of_cal_quarter (DATE)
  - end_of_fis_quarter (DATE)
  - calendar_quarter_number (INTEGER)
  - fiscal_quarter_number (INTEGER)
  - calendar_year (INTEGER)
  - calendar_year_id (INTEGER)
  - fiscal_year (INTEGER)
  - fiscal_year_id (INTEGER)
  - days_in_cal_year (INTEGER)
  - days_in_fis_year (INTEGER)
  - end_of_cal_year (DATE)
  - end_of_fis_year (DATE)
Sample rows:
  [('2019-05-31', 'Friday', 5, ..., '2019-12-27')]
--------------------------------------------------
Table full name: channels
Columns:
  - channel_id (INTEGER)
  - channel_desc (TEXT)
  - channel_class (TEXT)
  - channel_class_id (INTEGER)
  - channel_total (TEXT)
  - channel_total_id (INTEGER)
Sample rows:
  [(2, 'Partners', 'Others', 14, 'Channel total', 1),
   (3, 'Direct Sales', 'Direct', 12, 'Channel total', 1)]
--------------------------------------------------
Table full name: sales
Columns:
  - prod_id (INTEGER)
  - cust_id (INTEGER)
  - time_id (DATE)
  - channel_id (INTEGER)
  - promo_id (INTEGER)
  - quantity_sold (INTEGER)
  - amount_sold (REAL)
Sample rows:
  [(13, 987, '2019-01-10', 3, 999, 1, 1232.16),
   (13, 1660, '2019-01-10', 3, 999, 1, 1232.16)]
--------------------------------------------------
Table full name: costs
Columns:
  - prod_id (INTEGER)
  - time_id (DATE)
  - promo_id (INTEGER)
  - channel_id (INTEGER)
  - unit_cost (REAL)
  - unit_price (REAL)
Sample rows:
  [(13, '2019-02-10', 999, 3, 813.07, 1237.31),
   (14, '2019-01-19', 999, 2, 886.45, 1108.99)]
--------------------------------------------------
Table full name: supplementary_demographics
Columns:
  - cust_id (INTEGER)
  - education (TEXT)
  - occupation (TEXT)
  - household_size (TEXT)
  - yrs_residence (INTEGER)
  - affinity_card (INTEGER)
  - cricket (INTEGER)
  - baseball (INTEGER)
  - tennis (INTEGER)
  - soccer (INTEGER)
  - golf (INTEGER)
  - unknown (INTEGER)
  - misc (INTEGER)
  - comments (TEXT)
Sample rows:
  [(100001, '< Bach.', 'Exec.', '2', 3, 0, 0, 0, 1, 1, 1, 0, 0, 'Thanks...'),
   (100002, 'Bach.', 'Prof.', '2', 4, 0, 1, 1, 1, 1, 1, 0, 0, "The more times...")]
--------------------------------------------------
Table full name: currency
Columns:
  - country (TEXT)
  - year (INTEGER)
  - month (INTEGER)
  - to_us (REAL)
Sample rows:
  [('Singapore', 2019, 5, 1.0),
   ('Singapore', 2019, 6, 1.0)]
--------------------------------------------------

External knowledge that might be helpful:
  None

Table names:
  ['countries', 'customers', 'promotions', 'products', 'times', 'channels', 'sales', 'costs', 'supplementary_demographics', 'currency']

Task:
What is the average projected monthly sales in USD for **France** in **2021**, considering only:
- product sales with promotions where `promo_total_id = 1`
- and channels where `channel_total_id = 1`

Instructions:
- Use each product’s monthly sales from **2019** and **2020**
- Compute the growth rate from 2019 → 2020 by product and month
- Apply that rate to project **2021** monthly sales
- Convert projected 2021 sales to USD using **2021** exchange rates
- Finally, average and list sales **by month**

Clarification:
> What is the average monthly projected sales in USD for France in 2021?  
> Please use data from 2019 and 2020 for projection.  
> Ensure all values are converted to USD based on the 2021 exchange rates.

**Instructions for SQL generation:**
- Think step-by-step
- Return a **single SQLite SQL query**
- Wrap the SQL with triple backticks and `sql`, like:

```sql
SELECT ...
````

**Additional SQL rules:**

* Return both name and ID when only one is specified
* Use `ABS()` for percentage decrease questions
* If asked about two related tables, return only the **last one**
* Keep decimal precision to **4 places**

```
```
