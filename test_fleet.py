from app import app

c = app.test_client()
with c.session_transaction() as s:
    s['username'] = 'admin'
    s['_fresh'] = True

r = c.get('/fleet_status_report')
html = r.get_data(as_text=True)
print('status:', r.status_code)
print('toggle_cards:', 'btnCards' in html)
print('toggle_table:', 'btnTable' in html)
print('table_el:', 'id="fleetTable"' in html)
print('sortFleetTable:', 'sortFleetTable' in html)
print('setFleetView:', 'setFleetView' in html)
print('logbook_link:', "url_for('logbook_data')" in html or '/logbook_data' in html)
print('mel_link:', "url_for('mel_itens')" in html or '/mel_itens' in html)
print('aog_link:', "url_for('out_of_service')" in html or '/out_of_service' in html)
print('top_atas_label:', 'Top ATAs' in html)
print('last_30d_label:', '30 days' in html or '30d' in html)
print('fleet_cards_view:', 'fleetCardsView' in html)
