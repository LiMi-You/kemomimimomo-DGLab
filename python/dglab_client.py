import logging
from pydglab_ws import FeedbackButton, Channel, RetCode, DGLabWSServer

async def handle_dglab_connection(server, client, gui, pulse_manager):
    await client.bind()
    gui.update_connection_status(True, client.target_id)
    logging.info(f"已与 App {client.target_id} 成功绑定")

    async for data in client.data_generator(FeedbackButton, RetCode):
        await process_dglab_event(data, client, gui, pulse_manager)

async def process_dglab_event(data, client, gui, pulse_manager):
    if isinstance(data, FeedbackButton):
        logging.info(f"App 触发了反馈按钮：{data.name}")

    if data == FeedbackButton.A1:
        logging.info("对方按下了 A 通道圆圈按钮，开始发送波形")
        gui.update_channel_status(Channel.A, True)
        pulse_manager.start_sending(client)

    elif data == FeedbackButton.A2:
        logging.info("对方按下了 A 通道暂停按钮，暂停发送波形")
        gui.update_channel_status(Channel.A, False)
        pulse_manager.stop_sending(client)

    elif data == FeedbackButton.B1:
        logging.info("对方按下了 B 通道圆圈按钮，开始发送波形")
        gui.update_channel_status(Channel.B, True)
        pulse_manager.start_sending(client)

    elif data == FeedbackButton.B2:
        logging.info("对方按下了 B 通道暂停按钮，暂停发送波形")
        gui.update_channel_status(Channel.B, False)
        pulse_manager.stop_sending(client)

    elif data == RetCode.CLIENT_DISCONNECTED:
        logging.info("App 已断开连接，你可以尝试重新扫码进行连接绑定")
        gui.update_connection_status(False)
        gui.update_channel_status(Channel.A, False)
        gui.update_channel_status(Channel.B, False)
        pulse_manager.stop_sending(client)
        await client.rebind()
        gui.update_connection_status(True, client.target_id)
        logging.info("重新绑定成功")