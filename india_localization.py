import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def to_ist(dt):
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(IST)

def format_datetime_ist(dt=None):
    if dt is None:
        dt = datetime.datetime.now(pytz.utc)
    ist_dt = to_ist(dt)
    return ist_dt.strftime("%d-%m-%Y %H:%M IST")

def format_date(dt=None):
    if type(dt) == datetime.date or type(dt) == datetime.datetime:
        return dt.strftime("%d-%m-%Y")
    if dt is None:
        dt = datetime.datetime.now(pytz.utc)
    return dt.strftime("%d-%m-%Y")

def format_date_report(dt=None):
    if type(dt) == datetime.date or type(dt) == datetime.datetime:
        return dt.strftime("%d %B %Y")
    if dt is None:
        dt = datetime.datetime.now(pytz.utc)
    return dt.strftime("%d %B %Y")

def format_inr(amount, include_symbol=True):
    """Format number with Indian comma system."""
    try:
        amount = float(amount)
        is_negative = amount < 0
        amount = abs(amount)
        s = f"{amount:.2f}"
        parts = s.split('.')
        integer_part = parts[0]
        decimal_part = parts[1]
        
        last_three = integer_part[-3:]
        other_numbers = integer_part[:-3]
        if other_numbers != '':
            last_three = ',' + last_three
            # group by 2 from the right
            grouped = []
            while len(other_numbers) > 0:
                grouped.append(other_numbers[-2:])
                other_numbers = other_numbers[:-2]
            grouped.reverse()
            other_numbers = ','.join(grouped)
            formatted = other_numbers + last_three + "." + decimal_part
        else:
            formatted = last_three + "." + decimal_part
        res = f"₹ {formatted}" if include_symbol else formatted
        return f"-{res}" if is_negative else res
    except (ValueError, TypeError):
        return str(amount)

def format_inr_short(amount, include_symbol=True):
    """Format into Cr / Lakh"""
    try:
        amount = float(amount)
        is_negative = amount < 0
        amount = abs(amount)
        if amount >= 10000000:
            res = f"{amount/10000000:.2f} Cr"
        elif amount >= 100000:
            res = f"{amount/100000:.2f} Lakh"
        else:
            res = format_inr(amount, include_symbol=False)
            
        res = f"₹ {res}" if include_symbol else res
        return f"-{res}" if is_negative else res
    except (ValueError, TypeError):
        return str(amount)

def get_financial_year(dt=None):
    if dt is None:
        dt = datetime.date.today()
    year = dt.year
    month = dt.month
    if month >= 4:
        return f"FY {year}-{str(year+1)[-2:]}"
    else:
        return f"FY {year-1}-{str(year)[-2:]}"

def get_fy_quarter(dt=None):
    if dt is None:
        dt = datetime.date.today()
    month = dt.month
    if month in [4, 5, 6]:
        return "Q1 (Apr-Jun)"
    elif month in [7, 8, 9]:
        return "Q2 (Jul-Sep)"
    elif month in [10, 11, 12]:
        return "Q3 (Oct-Dec)"
    else:
        return "Q4 (Jan-Mar)"

if __name__ == "__main__":
    print(format_datetime_ist())
    print(format_inr(12500000))
    print(format_inr_short(12500000))
    print(get_financial_year())
    print(get_fy_quarter())
