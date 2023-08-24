# -*- coding: utf-8 -*-
#########################################################################
# -40001	签名验证错误
# -40002	xml/json解析失败
# -40003	sha加密生成签名失败
# -40004	AESKey 非法
# -40005	ReceiveId 校验错误
# -40006	AES 加密失败
# -40007	AES 解密失败
# -40008	解密后得到的buffer非法
# -40009	base64加密失败
# -40010	base64解密失败
# -40011	生成xml/json失败
#########################################################################
WXBizMsgCrypt_OK = 0
WXBizMsgCrypt_ValidateSignature_Error = -40001
WXBizMsgCrypt_ParseXml_Error = -40002
WXBizMsgCrypt_ComputeSignature_Error = -40003
WXBizMsgCrypt_IllegalAesKey = -40004
WXBizMsgCrypt_ValidateCorpid_Error = -40005
WXBizMsgCrypt_EncryptAES_Error = -40006
WXBizMsgCrypt_DecryptAES_Error = -40007
WXBizMsgCrypt_IllegalBuffer = -40008
WXBizMsgCrypt_EncodeBase64_Error = -40009
WXBizMsgCrypt_DecodeBase64_Error = -40010
WXBizMsgCrypt_GenReturnXml_Error = -40011
