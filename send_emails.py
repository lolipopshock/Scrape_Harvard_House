from bs4 import BeautifulSoup
from functools import reduce
import glob
import numpy as np
import os 
import pandas as pd
from datetime import datetime

import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def load_html(table_name):
    """Get Necessary table data from given html file
    """
    
    ## Load Table
    soup = BeautifulSoup(open(table_name))
    
    ## Get House names
    heads = soup.find(id="hideMap").find_all("h3")
    heads_data = [ele.text.split(':')[-1].strip().split(' - ') for ele in heads]

    ## Get House Features 
    # Ref to https://stackoverflow.com/questions/23377533/python-beautifulsoup-parsing-table
    tables = soup.find(id="hideMap").find_all("table")
    tables_data = []
    for table in tables:
        table_data = []
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [[ele['data-label'], ele.text.strip()] for ele in cols]
            table_data.append([ele for ele in cols if ele])
        tables_data.append(table_data)
        
    return heads_data, tables_data


def clean_html_data(heads_data, tables_data):
    """Obtain cleaned table via the html data
    """
    
    ## Merge the two input information
    res = []
    for head, house_info in zip(heads_data, tables_data):
        
        cur_table = pd.DataFrame([[item[1] for item in item_info] for item_info in house_info], 
             columns = [item[0] for item in house_info[0]])
        cur_table['Apartment'] = head[0] + ' ' + cur_table['Apartment']
        new_features = head[1].split(', ')
        for new_feature in new_features:
            val, key = new_feature.split(' ')
            if key[-1] == 's':
                key = key[:-1]
            cur_table[key] = val
        res.append(cur_table)
    
    df = reduce(pd.DataFrame.append, res). \
            drop(columns=['AvailableFrom', "AvailableTo", 'Amenities', 'Action']). \
            set_index('Apartment').sort_values('Bedroom', ascending=False)
    del df.index.name
    return df

def load_latest(path):
    path = os.path.join(path, "*.csv")
    filenames = glob.glob(path)
    birthtime = [os.path.getmtime(filename) for filename in filenames]
    return filenames[np.argmax(birthtime)]


def generate_sending_strings(html_name, history_path):

    cur_table = clean_html_data(*load_html(html_name))
    old_table = pd.read_csv(load_latest(history_path), index_col=0)
    cur_table.to_csv(os.path.join(history_path, \
                 f"{datetime.now().strftime('%m%d-%H%M%S')}.csv"))

    new_houses = list(cur_table.index.difference(old_table.index))
    drop_houses = list(old_table.index.difference(cur_table.index))

    house_change = f'<p>There are {len(new_houses)} new house(s): {new_houses} </p>' + \
    f'<p>There are {len(drop_houses)} dropped house(s): {drop_houses}</p>'

    show_table = cur_table.rename(index={i:'***'+i+'***' for i in new_houses})

    sending_strings = show_table.to_html() + house_change
                                  
    return sending_strings


def send_emails(to_addrs, sending_strings):
    mail_username='some@fancy.gmail'
    mail_password='whatalooooooooongpassword'
    from_addr = mail_username

    # HOST AND PORT
    HOST = 'smtp.gmail.com' # This is for gamil
    PORT = 587 
    smtp = smtplib.SMTP()
    print('connecting ...')
    #smtp.set_debuglevel(1)

    # Connect
    try:
        smtp.connect(HOST,PORT)
        smtp.starttls()
    except:
        print('CONNECT ERROR ****')

    # Login
    try:
        print('loginning ...')
        smtp.login(mail_username,mail_password)
    except:
        print('LOGIN ERROR ****')

    # fill content with MIMEText's object 
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Harvard House Information"
    message["From"] = from_addr
    message["To"] = ';'.join(to_addrs)

    part1 = MIMEText(sending_strings, "html")
    message.attach(part1)

    smtp.sendmail(from_addr, to_addrs, message.as_string())
    smtp.quit()
    print('Succesfully Send the email.')


if __name__ == "__main__":
    history_path = '.'
    html_name = 'test.html'     
    to_addrs = ['test@test.test']
    sending_strings = generate_sending_strings(html_name, history_path)
    send_emails(to_addrs, sending_strings)
