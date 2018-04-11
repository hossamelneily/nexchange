import os
from nexchange.utils import AESCipher
from django.conf import settings


class RpcMapper:
    PWS = {
        'rpc1': 'ove9n97G6tv3N8WUFdQKtgugeMGpqkYQmoHZI+jXl5rNAnAkT0Hgg'
                'F8jDuVsgXZS/QjETkQuMihsLqIDSojcRmH7piN8BSafOFG36GijxZo=',
        'rpc2': '8b2Dqw+FKwZ1pv/sAtsJUVKlz/z33zdRrivkiRIpVHWTXlilCxeYW'
                'DeQ8AjcyVK7bXReUqchn8pKAqbLYN7mG0CE+i81Ka8x3aYGaBF1hLY=',
        'rpc3': 'r7MC29tWNB1MM8elBEqrMn9IDUuPT3nzS08htosaBaJxixBFk4qsQa'
                '/aULRB/LSN6JlLu3Lr3bumPdWBc1ossuxb1/d8Mswy+MJuwJ3QBgc=',
        'rpc4': 'S5iAXq8gKpAFDMFiPzjEgVlw5vnycE4e1+A2xEBS464b2xLyayiinW'
                'qsn9f4EKFuRifZdZnBHmPKvT7iIpEOJJCNwwsonmysPDIyUURLoy4=',
        'rpc5': 'Z0DkkAwJqPJ7dx6ykAOT5lqwY5VpYlG16yhL4bU4D9zi4u4jQeqf3Pdc'
                '0KdE7f6nMdVX7QYhzwZddKlXK9zZfiiR2OutX6VLZuQmTEl4fJ0=',
        'rpc6': 'DCz4BziQRj7o+gwK2POJtcfNwVn++GXJ6Y80P2frgCU6hsMwcu1022'
                'AyHTlm7nDeBSbwir/B5qWJTrWrLDMxBNfW8MzpVMrd7fk82sPTzGU=',
        'rpc7': 'PbGnX+pDzdNZOVZ9EefGrBFMw9c8oTJxddtWsjbNINDJOai5zvK3spG'
                'YWg/yNaX+S3wjX7t0K1bl/GgZZtxSKU7OXrXQqoPjMUil6JxU7+Q=',
        # FIXME: What kind of hash should be placed here? (Oleg?)
        'rpc8': 'PbGnX+pDzdNZOVZ9EefGrBFMw9c8oTJxddtWsjbNINDJOai5zvK3spG'
                'YWg/yNaX+S3wjX7t0K1bl/GgZZtxSKU7OXrXQqoPjMUil6JxU7+Q=',
        'rpc9': 'PbGnX+pDzdNZOVZ9EefGrBFMw9c8oTJxddtWsjbNINDJOai5zvK3spG'
                'YWg/yNaX+S3wjX7t0K1bl/GgZZtxSKU7OXrXQqoPjMUil6JxU7+Q=',
    }

    @classmethod
    def get_rpc_addr(cls, node):
        protocol = 'http'
        prefix = 'RPC'
        user_env = '{}_{}_{}'.format(prefix, node.upper(), 'USER')
        pass_env = '{}_{}_{}'.format(prefix, node.upper(), 'PASSWORD')
        host_env = '{}_{}_{}'.format(prefix, node.upper(), 'HOST')
        port_env = '{}_{}_{}'.format(prefix, node.upper(), 'PORT')
        kwargs = {
            'protocol': protocol,
            'user': os.getenv(user_env, settings.DEFAULT_RPC_USER),
            'passwd': os.getenv(pass_env, settings.DEFAULT_RPC_PASS),
            'host': os.getenv(host_env, settings.DEFAULT_RPC_HOST),
            'port': os.getenv(port_env, None),
        }
        return '{protocol}://{user}:{passwd}@{host}:{port}'.format(**kwargs),\
               kwargs

    @classmethod
    def get_raw_pw(cls, node):
        return cls.PWS[node]

    @classmethod
    def get_key_pw(cls, node):
        prefix = 'RPC'
        env = '{}_{}_{}'.format(prefix, node.upper(), 'K')
        return os.getenv(env)

    @classmethod
    def get_pass(cls, node):
        raw_pass = RpcMapper.get_raw_pw(node)
        pass_key = RpcMapper.get_key_pw(node)
        cipher = AESCipher(pass_key)
        return cipher.decrypt(raw_pass)
