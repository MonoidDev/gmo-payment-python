# coding: utf-8
import requests
import urlparse
from errors import Error

API_BASE_URL = 'https://p01.mul-pay.jp/payment/'
DEFAULT_TIMEOUT = 30


class ResponseError(Exception):

    def __init__(self, response):
        self.error = self.parse(response.data)

    def __str__(self):
        return "Response contains Error" + repr(self.error)

    def __repr__(self):
        return self.__str__()

    def parse(self, response):
        return [Error(i) for i in response['ErrInfo'].split('|')]


class Response(object):

    def __init__(self, response_text):
        self.data = self.decode(response_text)
        self.ok = bool('ErrCode' not in self.data)

    def decode(self, response_text):
        response_dict = urlparse.parse_qs(response_text)
        # parse_qs は {"key": ["value"]} という dict を返却するので，扱いやすいように {"key": "value"} に変換する
        return {k: v[0] for k, v in response_dict.items()}


class BaseAPI(object):

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout

    def _requests(self, method, path, **kwargs):

        response = method(API_BASE_URL + path, timeout=self.timeout, **kwargs)

        response.raise_for_status()

        print response.text
        # assert False

        response = Response(response.text)

        if not response.ok:
            raise ResponseError(response)

        return response

    def get(self, path, **kwargs):
        return self._requests(requests.get, path, **kwargs)

    def post(self, path, **kwargs):
        return self._requests(requests.post, path, **kwargs)

    def assertRequiredOptions(self, key, options):
        for i in key:
            assert i in options


class Member(BaseAPI):

    def save(self, options={}):
        """
            指定されたサイトに会員を登録します。

            SiteID  char(13)
            SitePass    char(20)
            MemberID    char(60)
            MemberName  char(255) 登録する名前
        """
        self.assertRequiredOptions(["SiteID", "SitePass", "MemberID"], options)
        return self.post("SaveMember.idpass", data=options)

    def update(self, options={}):
        """
            指定されたサイトに会員情報を更新します。
            SiteID  char(13)
            SitePass    char(20)
            MemberID    char(60)
            MemberName  char(255) 更新する名前
        """
        self.assertRequiredOptions(["SiteID", "SitePass", "MemberID"], options)
        return self.post("UpdateMember.idpass", data=options)

    def delete(self, options={}):
        """
            指定したサイトから会員情報を削除します。
            SiteID  char(13)
            SitePass    char(20)
            MemberID    char(60)
        """

        self.assertRequiredOptions(["SiteID", "SitePass", "MemberID"], options)
        return self.post("DeleteMember.idpass", data=options)

    def search(self, options={}):
        pass


class Card(BaseAPI):
    pass


class Trade(BaseAPI):
    pass


class Tran(BaseAPI):

    def entry(self, options={}):
        """
            取引登録 API
            これ以降の決済取引で必要となる取引 ID と取引パスワードの発行を行い、取引を開始します。

            ShopID  char(13)
            ShopPass    char(10)
            OrderID char(27)    取引を識別するID
            JobCd   char    処理区分 CHECK / CAPTURE / AUTH / SAUTH
            Amount  number(7)   処理区分が有効性チェック(CHECK)を除き必須，利用金額
            Tax number(7) 税送料
            TdFlag char(1)  本人認証サービスを使用するかどうか 0 or 1
            TdTenantName    char    3Dセキュア表示店舗名
        """
        # TODO 3D セキュア系は後で実装する

        self.assertRequiredOptions(['ShopID', 'ShopPass', 'OrderID', 'JobCd'], options)
        assert options["JobCd"] == "CHECK" or options["Amount"] is not None

        return self.post('EntryTran.idPass', data=options)

    def execute(self, options={}):
        """
            決済実行 API
            お客様が入力したカード番号と有効期限の情報でカード会社と通信を行い決済を実施し、結果を返します。

            AccessID    char(32)
            AccessPass  char(32)
            OrderID     char(27)
            Method      char(1)    1(一括), 2(分割), 3(ボーナス一括), 4(ボーナス分割), 5(リボ), 処理区分 JobCdがCHECKの場合以外必要
            PayTimes    number(2)   支払い回数，Methodが分割，ボーナス分割を示している場合は必須
            CardNo      char(16)
            Expire      char(4)     YYMM カード有効期限
            PIN         char(4)     決済に使用するクレジッドカードの暗証番号を設定(別途オプション契約が必要)
            ClientField1 char(100) 自由項目
            ClientField2 char(100)
            ClientField3 char(100)
            ClientFieldFlag char(1)
        """
        self.assertRequiredOptions(['AccessID', 'AccessPass', 'OrderID', 'CardNo', 'Expire'], options)
        assert ('Method' not in options or options['Method'] % 2 != 0) or 'PayTimes' in options

        return self.post('ExecTran.idPass', data=options)


class GMOPG(object):

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.tran = Tran(timeout=timeout)
