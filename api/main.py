from api.video_resize import videoHandle
from flask import Flask, request, redirect, jsonify
from flask import Blueprint

bp=Blueprint("main",__name__)

@bp.route('/file-upload', methods=['POST'])
def upload_file():
	async_result=videoHandle.delay(request.files['file'].read())
	while (async_result.status == 'PENDING'):
		async_result.status
	if async_result.status == "FAILURE":
		resp = jsonify({'message': 'AN error occurred please check the file'})
		resp.status_code = 500
		log.error('Test %s failed with response status code %s.' % (inspect.stack()[0][3], resp.status_code))
	elif async_result.status == "SUCCESS":
		return_value = async_result.get()
		resp = jsonify({'message': 'File successfully uploaded', 'file': return_value})
		resp.status_code = 201
	return resp
