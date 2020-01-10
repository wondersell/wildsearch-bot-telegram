import json

import falcon
from sentry_sdk.integrations.falcon import FalconIntegration
from telegram import Bot

from .scrapinghub_helper import *

# загружаем конфиг
env.read_envfile()

# включаем логи
logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# включаем Sentry
if env('SENTRY_DSN', default=None) is not None:
    sentry_sdk.init(env('SENTRY_DSN'), integrations=[FalconIntegration()])


def get_cat_update_users():
    return env('WILDSEARCH_TEST_USER_LIST').split(',')


class CallbackCategoryExportResource(object):
    def on_post(self, req, resp):
        if req.has_param('chat_id'):
            bot.send_message(chat_id=req.get_param('chat_id'), text='Выгрузка данных по категории готова')
            resp.status = falcon.HTTP_200
            resp.body = json.dumps({'status': 'ok'})
        else:
            resp.status = falcon.HTTP_500
            resp.body = json.dumps({'error': 'wrong_chat_id'})


class CallbackCategoryListResource(object):
    def on_post(self, req, resp):
        comparator = WbCategoryComparator()
        comparator.load_from_api()
        comparator.calculate_diff()

        added_count = comparator.get_categories_count('added')
        removed_count = comparator.get_categories_count('removed')

        added_unique_count = comparator.get_categories_unique_count('added')

        if added_unique_count == 0:
            message = f'За последние сутки на Wildberries не добавилось категорий'
            send_export = False
        else:
            send_export = True
            comparator.dump_to_tempfile('added')
            comparator.dump_to_tempfile('removed')

            message = f'Обновились данные по категориям на Wildberries. C последнего  обновления добавилось ' \
                      f'{added_count} категорий, из них {added_unique_count} уникальных. Скрылось ' \
                      f'{removed_count} категорий'

        for uid in get_cat_update_users():
            bot.send_message(chat_id=uid, text=message)
            if send_export is True:
                bot.send_document(chat_id=uid, document=comparator.get_from_tempfile('added'))
                bot.send_document(chat_id=uid, document=comparator.get_from_tempfile('removed'))

        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'status': 'ok'})


bot = Bot(env('TELEGRAM_API_TOKEN'))

app = falcon.API()
app.req_options.auto_parse_form_urlencoded = True

app.add_route('/callback/category_export', CallbackCategoryExportResource())
app.add_route('/callback/category_list', CallbackCategoryListResource())
