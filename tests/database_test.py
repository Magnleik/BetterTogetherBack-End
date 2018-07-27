import datetime
import json
import math

from backend.DB.api import app, db
from flask import request
import unittest

from backend.DB.api import routes, tables
from backend.DB.api.tables import Reward


token = "?token=TEST"


class DatabaseTester(unittest.TestCase):


    def setUp(self):
        # Create a new database for each test
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.app = app.test_client()
        db.create_all()
        # Test users
        data = [
            {'active': 1, 'name': 'Per Pål', 'username': 'test1'},
            {'active': 1, 'name': 'Per Pål', 'username': 'test2'},
            {'active': 1, 'name': 'Per Pål', 'username': 'test3'},
            {'active': 1, 'name': 'Per Pål', 'username': 'test4'},
            {'active': 1, 'name': 'Per Pål', 'username': 'test5'},
        ]
        for user in data:
            self.app.post('/api/user/add%s' % token, data=json.dumps(user), content_type='application/json')

    def tearDown(self):
        # Empty db after each test
        db.session.remove()
        db.drop_all()

    def test_db_filled(self):
        # Verify that all users have been added to the db
        rv = self.app.get('/api/user/all%s' % token)
        self.assertEqual(5, len(rv.json))

    def test_disable_and_update_user(self):

        user = {'username': 'test2', 'name': 'updated', 'active': 0}
        rv = self.app.put(
            '/api/user/update%s' % token, data=json.dumps(user),
            content_type='application/json')
        self.assertFalse(rv.json[0].get('active'))

    def test_delete_user(self):
        rv = self.app.delete('/api/user/delete/test1%s' % token)
        self.assertEqual(rv.json.get('message'), 'test1 deleted')
        rv = self.app.get('/api/user/all%s' % token)
        user_json = {'active': 1, 'name': 'Per Pål', 'username': 'test1'}
        self.assertNotIn(user_json, rv.json)

    def test_get_active_users(self):
        data = {'username': 'test2', 'name': 'updated', 'active': False}
        self.app.put('/api/user/update%s' % token, data=json.dumps(data), content_type='application/json')
        rv = self.app.get('/api/user/active%s' % token)
        users = rv.json
        usernames = []
        for user in users:
            usernames.append(user.get('username'))
        self.assertNotIn('test2', usernames)
        self.assertIn('test3', usernames)

    def test_add_and_get_pair(self):
        date = math.floor(datetime.datetime.now().timestamp() * 1000)
        pair = {'date': date, 'person1': 'test1', 'person2': 'test3'}
        rv = self.app.post('/api/pair/add%s' % token, data=json.dumps(pair), content_type='application/json')
        json_file = rv.json
        self.assertEqual(pair, json_file)

        rv = self.app.get('/api/pair/all%s' % token)
        pairs = rv.json
        output = []
        for pair in pairs:
            output.append(pair.get('date'))
        self.assertIn(date, output)

    def test_get_pair_with_user(self):
        date = math.floor(datetime.datetime.now().timestamp() * 1000)
        pair = {'date': date, 'person1': 'test1', 'person2': 'test3'}

        self.app.post('/api/pair/add%s' % token, data=json.dumps(pair), content_type='application/json')

        rv = self.app.get('/api/pair/with_user/test1%s' % token)
        self.assertIn(pair, rv.json.get('pairs'))

        rv = self.app.get('/api/pair/with_user/test2%s' % token)
        self.assertNotIn(pair, rv.json.get('pairs'))

    def test_get_pair_after_reward(self):
        date = math.floor(datetime.datetime.now().timestamp() * 1000)
        reward = {'reward_type': 'pizza', 'date': date}
        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward), content_type='application/json')
        rv = self.app.get('/api/pair/all/after_last_reward/pizza%s' % token)
        pairs = rv.json
        self.assertEqual(0, len(pairs))
        pair = {'date': date, 'person1': 'test1', 'person2': 'test3'}
        self.app.post('/api/pair/add%s' % token, data=json.dumps(pair), content_type='application/json')
        rv = self.app.get('api/pair/all/after_last_reward/pizza%s' % token)
        pairs = rv.json
        self.assertEqual(1, len(pairs))

    def test_get_pair_after_date(self):
        # Test pairs
        pair1 = {'person1': 'test1', 'person2': 'test2'}
        pair2 = {'person1': 'test3', 'person2': 'test4'}
        # Add a pair, get a timestamp after and add second pair
        self.app.post('/api/pair/add%s' % token, data=json.dumps(pair1), content_type='application/json')
        date = math.floor(datetime.datetime.now().timestamp() * 1000)
        self.app.post('/api/pair/add%s' % token, data=json.dumps(pair2), content_type='application/json')
        # Get all pairs after the date
        rv = self.app.get(('/api/pair/all/after_date/%d%s' % (date, token)))
        pairs = rv.json.get('pairs')
        # Check that only the second pair is gotten from the query
        self.assertEqual(1, len(pairs))
        self.assertIn(pair2.get('person1'), pairs[0].get('person1'))

    def test_update_pair(self):
        date = math.floor(datetime.datetime.now().timestamp() * 1000)
        pair1 = {'person1': 'test1', 'person2': 'test2', 'date': date}

        self.app.post('/api/pair/add%s' % token, data=json.dumps(pair1), content_type='application/json')

        pair1 = {'person1': 'test3', 'person2': 'test2'}

        self.app.put(('/api/pair/at_date/update/%d%s' % (date, token)),
                     data=json.dumps(pair1), content_type='application/json')

        rv = self.app.get('/api/pair/at_date/get/%d%s' % (date, token))
        self.assertEqual('test3', rv.json.get('person1'))

    def test_get_pair_count(self):
        pair1 = {'person1': 'test1', 'person2': 'test2'}
        pair2 = {'person1': 'test2', 'person2': 'test1'}
        pair3 = {'person1': 'test1', 'person2': 'test3'}
        self.app.post('/api/pair/add%s' % token, data=json.dumps(pair1), content_type='application/json')
        self.app.post('/api/pair/add%s' % token, data=json.dumps(pair2), content_type='application/json')
        self.app.post('/api/pair/add%s' % token, data=json.dumps(pair3), content_type='application/json')
        response = self.app.get('/api/pair/count_pair%s' % token).json
        self.assertEqual(2, len(response))
        self.assertEqual(2, response[0]['total'])
        self.assertEqual(1, response[1]['total'])

    def test_get_reward_count(self):
        reward1 = {'reward_type': 'pizza'}
        reward2 = {'reward_type': 'cake'}
        reward3 = {'reward_type': 'pizza'}

        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward1), content_type='application/json')
        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward2), content_type='application/json')
        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward3), content_type='application/json')

        rewards = self.app.get('/api/reward/all%s' % token).json
        self.assertEqual(3, len(rewards))
        count = self.app.get('api/reward/unused/pizza%s' % token).json
        self.assertEqual(2, count)
        count = self.app.get('api/reward/unused/cake%s' % token).json
        self.assertEqual(1, count)

    def test_use_reward(self):
        reward1 = {'reward_type': 'pizza'}
        reward2 = {'reward_type': 'cake'}
        reward3 = {'reward_type': 'pizza'}

        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward1), content_type='application/json')
        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward2), content_type='application/json')
        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward3), content_type='application/json')

        self.app.put('/api/reward/use/pizza%s' % token)
        count = self.app.get('/api/reward/unused/pizza%s' % token).json

        self.assertEqual(1, count)

    def test_get_earliest_unused_reward(self):
        date = math.floor(datetime.datetime.now().timestamp() * 1000)

        reward1 = {'reward_type': 'pizza', 'date': date}
        reward2 = {'reward_type': 'cake'}
        reward3 = {'reward_type': 'pizza'}

        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward1), content_type='application/json')
        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward2), content_type='application/json')
        self.app.post('/api/reward/add%s' % token, data=json.dumps(reward3), content_type='application/json')

        reward = self.app.get('/api/reward/unused/earliest/pizza%s' % token).json[0]

        self.assertEqual(reward['date'], date)

    def test_add_and_get_threshold(self):
        threshold1 = {'threshold': 50, 'reward_type': 'pizza'}
        threshold2 = {'threshold': 42, 'reward_type': 'cake'}
        self.app.post('/api/threshold/add%s' % token, data=json.dumps(threshold1), content_type='application/json')
        self.app.post('/api/threshold/add%s' % token, data=json.dumps(threshold2), content_type='application/json')
        threshold = self.app.get('/api/threshold/get/pizza%s' % token).json[0].get('threshold')
        self.assertEqual(50, threshold)
        threshold = self.app.get('/api/threshold/get/cake%s' % token).json[0].get('threshold')
        self.assertEqual(42, threshold)

    def test_update_threshold(self):
        data = {'threshold': 50, 'reward_type': 'pizza'}
        self.app.post('/api/threshold/add%s' % token, data=json.dumps(data), content_type='application/json')
        updated_info = {'threshold': 42}
        self.app.put('/api/threshold/update/pizza%s' % token,
                     data=json.dumps(updated_info), content_type='application/json')
        threshold = self.app.get('/api/threshold/get/pizza%s' % token).json[0].get('threshold')
        self.assertEqual(42, threshold)

    def test_wrong_input(self):
        faulty_data = {'wrong': 'this is wrong'}
        response = self.app.post('/api/user/add%s' % token,
                                 data=json.dumps(faulty_data), content_type='application/json')
        self.assertEqual(400, response.status_code)
        response = self.app.post('/api/pair/add%s' % token,
                                 data=json.dumps(faulty_data), content_type='application/json')
        self.assertEqual(400, response.status_code)
        response = self.app.post('/api/reward/add%s' % token,
                                 data=json.dumps(faulty_data), content_type='application/json')
        self.assertEqual(400, response.status_code)
        response = self.app.post('/api/threshold/add%s' % token,
                                 data=json.dumps(faulty_data), content_type='application/json')
        self.assertEqual(400, response.status_code)

    def test_wrong_token(self):
        response = self.app.get('/api/user/all?token=wrong_token')
        self.assertEqual(403, response.status_code)
