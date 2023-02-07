import os
from urllib.parse import quote_plus

import boto3
import streamlit as st

from microarchive import MicroArchive, Identity, Contact, Description, Item

THUMB_DIR = ".thumb"

TITLE = "title"
DATE_DESC = "datedesc"
EXTENT = "extent"
BIOG_HIST = "bioghist"
SCOPE = "scope"
LANGS = "langs"
HOLDER = "holder"
STREET = "street"
POSTCODE = "postcode"

EXPIRATION = 3600
SITE_ID = "siteid"
SITE_SUFFIX = "sitesuffix"


def value_or_default(key, default = ""):
    return st.session_state[key] if key in st.session_state else default


def aws_client(service: str):
    return boto3.client(service,
                        region_name=st.secrets.s3_credentials.region,
                        aws_access_key_id=st.secrets.s3_credentials.access_key,
                        aws_secret_access_key=st.secrets.s3_credentials.secret_key,)


@st.experimental_memo(ttl=EXPIRATION)
def load_files():
    s3 = aws_client('s3')
    r = s3.list_objects_v2(
        Bucket=st.secrets.s3_credentials.bucket,
        Prefix=st.secrets.s3_credentials.prefix)
    file_meta = [meta for meta in r["Contents"] if not meta["Key"].endswith("/")]
    items = []
    for i, meta in enumerate(file_meta):
        key: str = meta["Key"]
        if THUMB_DIR in key:
            continue

        path_no_ext = os.path.splitext(key)[0]
        item_id = path_no_ext[len(st.secrets.s3_credentials.prefix):]
        url = st.secrets.iiif.server_url + quote_plus(key) + "/full/max/0/default.jpg"
        thumb_url = st.secrets.iiif.server_url + quote_plus(key) + "/full/!75,100/0/default.jpg"
        items.append((item_id, url, thumb_url))
    return items


def init_page():
    if "items" not in st.session_state:
        st.session_state.items = load_files()

    if TITLE not in st.session_state:
        st.session_state[TITLE] = "Default Collection Name"
    if SCOPE not in st.session_state:
        st.session_state[SCOPE] = "[Default collection description.]"

    st.write("# Micro Archive Publication Tool")


def get_random_string(length: int) -> str:
    import random, string
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def upload(name: str, site_suffix: str, index: str, xml: str, json: str):
    """Publish data to a Cloudfront distribution..."""

    bucket = st.secrets.s3_credentials.bucket
    file_prefix:str = st.secrets.s3_credentials.prefix
    file_prefix_no_slash = file_prefix[:-1] if file_prefix.endswith("/") else file_prefix
    # the suffix for the uploaded material, on top of the
    # suffix for the input files
    suffix = f"_webdata_{site_suffix}/"
    key_prefix = file_prefix_no_slash + suffix

    files = [
        ("index.html", "text/html", index),
        (f"{name}.xml", "text/xml", xml),
        (f"{name}.json", "application/json", json),
    ]

    s3 = aws_client('s3')
    for filename, content_type, data in files:
        s3.put_object(
            ACL='public-read',
            Bucket=bucket,
            Key=key_prefix + filename,
            ContentType=content_type,
            Body=data.encode('utf-8')
        )


def make_archive():
    def key(id: str) -> str:
        return f"{id}.title"

    def scope(id: str) -> str:
        return f"{id}.scope"

    return MicroArchive(
        identity=Identity(
            title=value_or_default(TITLE),
            datedesc=value_or_default(DATE_DESC, ""),
            extent=value_or_default(EXTENT)),
        contact=Contact(
            holder=value_or_default(HOLDER),
            street=value_or_default(STREET),
            postcode=value_or_default(POSTCODE)),
        description=Description(biog=value_or_default(BIOG_HIST),
                                scope=value_or_default(SCOPE),
                                lang=value_or_default(LANGS, [])),
        items=[Item(
            ident,
            Identity(value_or_default(key(ident))),
            Description(scope=value_or_default(scope(ident))), url, thumb_url, [])
            for ident, url, thumb_url in value_or_default("items", [])]
    )


def create_site(name: str, site_suffix: str):
    bucket = st.secrets.s3_credentials.bucket
    region = st.secrets.s3_credentials.region
    file_prefix:str = st.secrets.s3_credentials.prefix
    file_prefix_no_slash = file_prefix[:-1] if file_prefix.endswith("/") else file_prefix
    # the suffix for the uploaded material, on top of the
    # suffix for the input files
    suffix = f"_webdata_{site_suffix}/"
    key_prefix = file_prefix_no_slash + suffix
    # Make a cloudfront distribution for the uploaded data
    cloudfront = aws_client('cloudfront')

    # s3.create_origin_access_policy()
    ref = get_random_string(10)
    bucket_domain = f"{bucket}.s3.{region}.amazonaws.com"

    origin_id = bucket + "_" + name
    if SITE_ID not in st.session_state:
        r = cloudfront.create_distribution(
            DistributionConfig={
                'CallerReference': ref,
                'Enabled': True,
                'DefaultRootObject': 'index.html',
                'HttpVersion': 'http2and3',
                'Comment': 'Created by the EHRI-3 WP11 Demo tool',
                'Origins': {
                    'Quantity': 1,
                    'Items': [{
                            'Id': origin_id,
                            'OriginPath': "/" + key_prefix[:-1],  # slash must be at the start
                            'DomainName': bucket_domain,
                            # 'OriginAccessControlId': oac_id,
                            'S3OriginConfig': {
                                'OriginAccessIdentity': ''
                            }
                    }]
                },
                'DefaultCacheBehavior': {
                    # 'CachePolicyId': '658327ea-f89d-4fab-a63d-7e88639e58f6',  # CachingOptimized (from docs)
                    'CachePolicyId': '4135ea2d-6df8-44a3-9df3-4b5a84be39ad',  # CachingDisabled (from docs)
                    'ResponseHeadersPolicyId': '5cc3b908-e619-4b99-88e5-2cf7f45965bd', # Allow CORS
                    'TargetOriginId': origin_id,
                    'ViewerProtocolPolicy': 'allow-all',
                    'AllowedMethods': {
                        'Quantity': 2,
                        'Items' : ['GET', 'HEAD'],
                        'CachedMethods': {
                            'Quantity': 2,
                            'Items': ['GET', 'HEAD']
                        }
                    }
                }
            }
        )

        with st.expander("View Distribution Info"):
            st.json(r["Distribution"])

        site_id = r["Distribution"]["DomainName"]
        st.session_state[SITE_ID] = site_id
        return site_id
    else:
        return st.session_state[SITE_ID]


