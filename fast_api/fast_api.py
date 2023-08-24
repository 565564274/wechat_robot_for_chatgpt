# -*- encoding:utf-8 -*-
import logging
import xml.etree.ElementTree as ET
import threading
import pprint

from callback.WXBizMsgCrypt3 import WXBizMsgCrypt
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils import resource_pool
from utils.log import logger_manager
from utils.save_file import save_file_by_url
from utils.save_message_to_file import MessageHistory
from fast_api.third_api.qyapi import QiyeApi
from fast_api.third_api.chatgpt import ChatgptApi
from fast_api.statics.static_api import static_app


logger = logger_manager.logger
app = FastAPI(docs_url=None, redoc_url=None)
static_dir = Path(__file__).parents[0] / "statics"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(static_app.router, prefix="", tags=[])


sToken = resource_pool["qyapi"]["sToken"]
sEncodingAESKey = resource_pool["qyapi"]["sEncodingAESKey"]
sCorpID = resource_pool["qyapi"]["qiye_id"]
wxcpt = WXBizMsgCrypt(sToken, sEncodingAESKey, sCorpID)
qy_kf_api = QiyeApi()
qy_kf_custom = {}
qy_kf_custom_messages = {}
qy_kf_custom_messages_media = {}
start = {"first": True}
chatgpt = ChatgptApi()
welcome_message = "回复【开始聊天】，开始与chatgpt对话\n" \
                  "回复【生成图片】，开始由OpenAI生成图片\n" \
                  "回复【退出】退出对话"
verify_userid = resource_pool["secret"]["verify_userid"]


lock = threading.Lock()
scheduler = AsyncIOScheduler()


def sync_messages_job():
    try:
        with lock:
            massage_job = MessageHistory()
            global qy_kf_custom
            qy_kf_custom = massage_job.sync(qy_kf_custom)
    except Exception as e:
        logger.error(e)


@app.on_event("startup")
async def startup_event():
    logger = logging.getLogger("uvicorn.access")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    log_file = logger_manager.log_file
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s[%(name)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)

    scheduler.add_job(sync_messages_job, 'cron', minute="30", second="30")
    scheduler.start()


@app.on_event('shutdown')
async def shutdown_event():
    sync_messages_job()
    scheduler.shutdown()
    logger.info("shutdown scheduler done")


@app.post("/sync_messages")
async def sync_messages(userid: str, messages: dict = None):
    if userid != verify_userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect userid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    massage_job = MessageHistory()
    global qy_kf_custom
    with lock:
        if messages:
            qy_kf_custom = massage_job.sync(messages)
        else:
            qy_kf_custom = massage_job.sync(qy_kf_custom)
    return qy_kf_custom


@app.get("/get_qy_kf_custom")
async def get_qy_kf_custom(userid: str, external_userid: str = None):
    if userid != verify_userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect userid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    global qy_kf_custom
    if external_userid:
        if external_userid in qy_kf_custom:
            return qy_kf_custom[external_userid]
        else:
            return "找不到这个external_userid"
    return qy_kf_custom


@app.get("/get_qy_kf_custom_messages")
async def get_qy_kf_custom_messages(userid: str, external_userid: str = None, want_custom: str = None):
    if userid != verify_userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect userid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    global qy_kf_custom_messages
    if external_userid:
        if external_userid in qy_kf_custom_messages:
            return qy_kf_custom_messages[external_userid]
        else:
            return "找不到这个external_userid"
    elif want_custom:
        return [i for i in qy_kf_custom_messages.keys()]
    return qy_kf_custom_messages


@app.get("/get_qy_kf_custom_messages_media")
async def get_qy_kf_custom_messages_media(userid: str, external_userid: str = None, want_custom: str = None):
    if userid != verify_userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect userid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    global qy_kf_custom_messages_media
    if external_userid:
        if external_userid in qy_kf_custom_messages_media:
            return qy_kf_custom_messages_media[external_userid]
        else:
            return "找不到这个external_userid"
    elif want_custom:
        return [i for i in qy_kf_custom_messages_media.keys()]
    return qy_kf_custom_messages_media


@app.get("/get_user_info_by_external_userid")
async def get_user_info_by_external_userid(userid: str, external_userid: str = None, need_enter_session_context: int = 1):
    if userid != verify_userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect userid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_info = qy_kf_api.get_user_info_by_external_userid(external_userid, need_enter_session_context)
    return user_info


@app.post("/update_chatgpt_key")
async def update_chatgpt_key(userid: str, key: str):
    if userid != verify_userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect userid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    global chatgpt
    chatgpt = ChatgptApi(key)
    return chatgpt.get_key()


@app.get("/message")
async def receive_message(request: Request):
    query = request.query_params

    if "msg_signature" not in query or "timestamp" not in query or "nonce" not in query:
        raise HTTPException(status_code=400, detail="参数不完整")

    # 解析查询参数
    sVerifyMsgSig = query["msg_signature"]
    sVerifyTimeStamp = query["timestamp"]
    sVerifyNonce = query["nonce"]
    sVerifyEchoStr = query.get("echostr")

    ret, sEchoStr = wxcpt.VerifyURL(sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr)
    # logger.info(ret, sEchoStr)
    if ret == 0:
        sEchoStr = sEchoStr.decode("utf-8")
        return int(sEchoStr)
    else:
        raise HTTPException(status_code=400, detail="ERR: VerifyURL ret: " + str(ret))


@app.post("/message")
async def receive_message(request: Request):
    logger.info("--------------------------------" * 6)
    query = request.query_params
    body = await request.body()

    if "msg_signature" not in query or "timestamp" not in query or "nonce" not in query:
        raise HTTPException(status_code=400, detail="参数不完整")

    # 解析查询参数
    sReqMsgSig = query["msg_signature"]
    sReqTimeStamp = query["timestamp"]
    sReqNonce = query["nonce"]
    sReqData = body
    # logger.info(sReqData)

    ret, sMsg = wxcpt.DecryptMsg(sReqData, sReqMsgSig, sReqTimeStamp, sReqNonce)
    # logger.info(sMsg)
    if ret == 0:
        message = {}
        xml_tree = ET.fromstring(sMsg)
        for child in xml_tree:
            tag = child.tag
            attrib = child.attrib
            text = child.text
            # message.update({tag: {"attrib": attrib, "text": text}})
            message.update({tag: {"text": text}})
        logger.info("回调收到的xml:")
        logger.info(pprint.pformat(message))
        msg_list = qy_kf_api.sync_msg(message["Token"]["text"], message["OpenKfId"]["text"])
        # 留存聊天记录
        global start
        global qy_kf_custom  # 所有聊天记录
        global qy_kf_custom_messages  # 每轮对话记录
        global qy_kf_custom_messages_media  # 每轮图片对话
        if start["first"]:
            start["first"] = False
            for item in msg_list[:-1]:
                if item["origin"] == 3:
                    if item["external_userid"] not in qy_kf_custom:
                        qy_kf_custom[item["external_userid"]] = [item]
                    else:
                        qy_kf_custom[item["external_userid"]].append(item)
                elif item["origin"] == 4:
                    if item["event"]["external_userid"] not in qy_kf_custom:
                        qy_kf_custom[item["event"]["external_userid"]] = [item]
                    else:
                        qy_kf_custom[item["event"]["external_userid"]].append(item)
                else:
                    pass

            # sync messages when first
            sync_messages_job()

            for external_userid in qy_kf_custom.keys():
                chat_text = False
                chat_media = False
                qy_kf_custom_messages[external_userid] = []
                qy_kf_custom_messages_media[external_userid] = [False, []]
                for item in qy_kf_custom[external_userid]:
                    # 消息来源。3-微信客户发送的消息 4-系统推送的事件消息 5-接待人员在企业微信客户端发送的消息
                    if item["origin"] == 3:
                        if item["msgtype"] != "text":
                            # 去掉非text类型的消息 e.g. voice/file/image
                            continue
                        if item["text"]["content"] == "开始聊天":
                            chat_text = True
                            chat_media = False
                            qy_kf_custom_messages[item["external_userid"]] = [["user", item["text"]["content"]]]
                            qy_kf_custom_messages_media[item["external_userid"]] = [False, []]
                        elif item["text"]["content"] == "生成图片":
                            chat_text = False
                            chat_media = True
                            qy_kf_custom_messages[item["external_userid"]] = []
                            qy_kf_custom_messages_media[item["external_userid"]] = [True, [item["text"]["content"]]]
                        elif item["text"]["content"] == "退出":
                            chat_text = False
                            chat_media = False
                            qy_kf_custom_messages[item["external_userid"]] = []
                            qy_kf_custom_messages_media[item["external_userid"]] = [False, []]
                        else:
                            if chat_text:
                                qy_kf_custom_messages[item["external_userid"]].append(["user", item["text"]["content"]])
                            elif chat_media:
                                qy_kf_custom_messages_media[item["external_userid"]][1].append(item["text"]["content"])
                            else:
                                pass
                    elif item["origin"] == 4:
                        pass
        else:
            logger.info("收到的聊天记录:")
            logger.info(pprint.pformat(msg_list))
        if msg_list:
            # 判断会话状态
            if msg_list[-1]["origin"] == 4:
                logger.info("收到origin=4,事件msg,直接返回")
                if msg_list[-1]["event"]["external_userid"] not in qy_kf_custom:
                    qy_kf_custom[msg_list[-1]["event"]["external_userid"]] = [msg_list[-1]]
                    qy_kf_custom_messages[msg_list[-1]["event"]["external_userid"]] = []
                    qy_kf_custom_messages_media[msg_list[-1]["event"]["external_userid"]] = [False, []]
                else:
                    qy_kf_custom[msg_list[-1]["event"]["external_userid"]].append(msg_list[-1])
                return ""
            service_state = qy_kf_api.get_service_state(msg_list[-1]["external_userid"], msg_list[-1]["open_kfid"])
            if service_state["service_state"] == 0:
                trans = qy_kf_api.transfer_service_state(msg_list[-1]["external_userid"], msg_list[-1]["open_kfid"], 1)
                assert trans["errmsg"] == "ok", f"trans failed: {trans}"
                logger.info("已经转换到智能助手接待")
            elif service_state["service_state"] == 1:
                logger.info("已经由智能助手接待")
            else:
                logger.info(service_state)
                assert False, "会话状态不可由API控制"

            # 处理对话
            item = msg_list[-1]
            if item["external_userid"] not in qy_kf_custom:
                qy_kf_custom[item["external_userid"]] = [item]
                qy_kf_custom_messages[item["external_userid"]] = []
                qy_kf_custom_messages_media[item["external_userid"]] = [False, []]
            else:
                qy_kf_custom[item["external_userid"]].append(item)

            if item["text"]["content"] == "开始聊天":
                qy_kf_custom_messages[item["external_userid"]] = [["user", item["text"]["content"]]]
                qy_kf_custom_messages_media[item["external_userid"]] = [False, []]
                qy_kf_api.send_msg(
                    msg_list[-1]["external_userid"],
                    msg_list[-1]["open_kfid"],
                    content="已经进入聊天模式，请输入对话"
                )
                logger.info(f"******回复：已经进入聊天模式，请输入对话")
                logger.info("--------------------------------" * 6)
            elif item["text"]["content"] == "生成图片":
                qy_kf_custom_messages[item["external_userid"]] = []
                qy_kf_custom_messages_media[item["external_userid"]] = [True, [item["text"]["content"]]]
                qy_kf_api.send_msg(
                    msg_list[-1]["external_userid"],
                    msg_list[-1]["open_kfid"],
                    content="已经进入生成图片模式，请输入描述"
                )
                logger.info(f"******回复：已经进入生成图片模式，请输入描述")
                logger.info("--------------------------------" * 6)
            elif item["text"]["content"] == "退出":
                qy_kf_custom_messages[item["external_userid"]] = []
                qy_kf_custom_messages_media[item["external_userid"]] = [False, []]
                qy_kf_api.send_msg(
                    msg_list[-1]["external_userid"],
                    msg_list[-1]["open_kfid"],
                    content=welcome_message
                )
                logger.info(f"******回复初始消息******")
                logger.info("--------------------------------" * 6)
            else:
                if qy_kf_custom_messages[item["external_userid"]]:
                    qy_kf_custom_messages[item["external_userid"]].append(["user", item["text"]["content"]])
                    t = threading.Thread(target=reply, args=(msg_list,))
                    t.start()
                elif qy_kf_custom_messages_media[item["external_userid"]][0]:
                    qy_kf_custom_messages_media[item["external_userid"]][1].append(item["text"]["content"])
                    t = threading.Thread(target=reply_media, args=(msg_list,))
                    t.start()
                else:
                    qy_kf_api.send_msg(
                        msg_list[-1]["external_userid"],
                        msg_list[-1]["open_kfid"],
                        content=welcome_message
                    )
                    logger.info(f"******回复初始消息******")
                    logger.info("--------------------------------" * 6)
        else:
            logger.info("没有msg_list，不回复")
        return ""
    else:
        raise HTTPException(status_code=400, detail="ERR: DecryptMsg ret: " + str(ret))


def reply(msg_list):
    global qy_kf_custom_messages
    messages = qy_kf_custom_messages[msg_list[-1]["external_userid"]]
    for i in range(len(messages)):
        if messages[-(i+1)][1] == "开始聊天":
            qy_kf_custom_messages[msg_list[-1]["external_userid"]] = messages[-(i+1):]
            send_message = chatgpt.chat(qy_kf_custom_messages[msg_list[-1]["external_userid"]])
            qy_kf_custom_messages[msg_list[-1]["external_userid"]].append([send_message["role"],
                                                                           send_message["content"]])
            break
        else:
            send_message = {"role": "assistant", "content": "回复【开始聊天】，开始与chatgpt对话"}
    send_result = qy_kf_api.send_msg(
        msg_list[-1]["external_userid"],
        msg_list[-1]["open_kfid"],
        content=send_message["content"]
    )
    logger.info(f"{send_result}")
    logger.info(f"回复消息:{send_message}")
    logger.info("--------------------------------" * 6)


def reply_media(msg_list):
    global qy_kf_custom_messages_media
    messages = qy_kf_custom_messages_media[msg_list[-1]["external_userid"]][1]
    for i in range(len(messages)):
        if messages[-(i+1)] == "生成图片":
            qy_kf_custom_messages_media[msg_list[-1]["external_userid"]][1] = messages[-(i+1):]
            is_true, image_url = chatgpt.image(qy_kf_custom_messages_media[msg_list[-1]["external_userid"]][1][-1])
            # 判断是否生成图片
            if not is_true:
                send_result = qy_kf_api.send_msg(
                    msg_list[-1]["external_userid"],
                    msg_list[-1]["open_kfid"],
                    content=image_url
                )
                logger.info(f"{send_result}")
                logger.info(f"回复消息:{image_url}")
                logger.info("--------------------------------" * 6)
                return
            # 保存图片
            file_name, file_path = save_file_by_url(image_url, msg_list[-1]["external_userid"])
            if not file_path:
                logger.error("上传素材失败")
                return
            # 上传素材
            media_id = qy_kf_api.upload_media(file_name, file_path)
            send_result = qy_kf_api.send_media(
                msg_list[-1]["external_userid"],
                msg_list[-1]["open_kfid"],
                media_id=media_id
            )
            logger.info(f"{send_result}")
            logger.info(f"已回复图片:{file_path}")
            logger.info("--------------------------------" * 6)
            break



