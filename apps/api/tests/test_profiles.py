from test_workspace import setup, login, course, lecture


def test_profiles_are_reusable_versioned_and_do_not_change_lectures(setup):
    app,client,_=setup
    headers=login(client)
    lec=lecture(client,headers,course(client,headers)['id'])
    body={'name':'Science','detail_prompt':'Keep worked examples','layout_prompt':'Group by concept','instructions':'Plain language'}
    saved=client.post('/prompt-profiles',json=body,headers=headers)
    assert saved.status_code==201,saved.text
    row=saved.json()
    assert client.post('/prompt-profiles',json=body,headers=headers).json()==row
    assert client.get('/prompt-profiles').json()==[row]
    assert client.get('/lectures/'+lec['id']+'/snapshot').json()['settings']['detail_prompt']==''
    update={**body,'instructions':'Explain equations','expected_version':1}
    h={**headers,'idempotency-key':'update-profile-123'}
    changed=client.put('/prompt-profiles/'+row['id'],json=update,headers=h)
    assert changed.status_code==200,changed.text
    assert changed.json()['version']==2
    assert client.put('/prompt-profiles/'+row['id'],json=update,headers={**h,'idempotency-key':'stale-profile-123'}).status_code==409
    assert client.post('/prompt-profiles',json=body,headers={'origin':headers['origin']}).status_code==403
