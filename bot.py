from io import BytesIO
import discord
import pandas as pd
import numpy as np
import datetime
import json

# Bot準備
TOKEN = 'YOUR-TOKEN-HERE' #　控えておいたToken

intents = discord.Intents.default()
intents.typing = False  # typingを受け取らないように
intents.members = True  # membersを受け取る

client = discord.Client(intents=intents)


# Bot起動時の処理
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


# 特定メッセージ送信時の処理
@client.event
async def on_message(message):
    # Bot自身のメッセージを無視
    if message.author == client.user:
        return

    # 疎通チェック
    if message.content.startswith('$ping'):
        await message.channel.send('pong')
        return

    # ロール一覧を取得
    if message.content.startswith('$getrole'):
        df = getRole(message)

        serverName = message.guild.name
        dt = datetime.datetime.today()
        currentTime = str(dt.date())
        fileName = 'csv/getRoles_' + serverName + '_' + currentTime + '.csv'
        df.to_csv(fileName, index=False,header=False, encoding='UTF-8')
        await message.channel.send(file=discord.File(fileName))
        return

    # smashgg csvファイルに関する挙動
    if message.content.startswith('$ggrole'):
        # 添付ファイルが1個だけの時、メインの処理を実行
        if len(message.attachments) == 1 and len(message.role_mentions) == 1:
            # ロールを取得
            role = message.role_mentions[0]
            await message.channel.send(role.name + 'を付与するよ')

            # 添付ファイルの読み込み、データフレームへ変換
            await message.channel.send('ファイル名: '+message.attachments[0].filename + 'を読み込み中だよ')
            file = await message.attachments[0].read()
            df = pd.read_csv(BytesIO(file))
            
            # 処理
            nameList = ggRole(message,df,role)

            # ロール付与
            for id in nameList['targetMemberList']:
                print('id')
                cur_member = message.guild.get_member(id)
                await cur_member.add_roles(role)
                print(message.guild.get_member(id).name + 'に付与できた')

            # ログ出力
            await message.channel.send(str(len(nameList['targetMemberList'])) + '人にロールを付与したよ')
            
            # 付与できなかった人たち
            await message.channel.send('付与できなかった人たち：')
            await message.channel.send(nameList['notFoundsList'])

        # 例外。memo: ファイルなしの呼び出しはgetroleにしてもいいかも。
        else:
            await message.channel.send('エラー！付与するロール一つをメンションして、添付ファイルを一つ添付してください。')
            await message.channel.send('例：$ggrole @nanka-role [添付ファイル.csv]')


    # # 開発一時停止。マトリクスでロールを管理する機能。あんま使わない気がして、、、 
    # if message.content.startswith('$modifyrole'):
    #     # 添付ファイルが1個だけの時、メインの処理を実行
    #     if len(message.attachments) == 1:
    #         # 添付ファイルの読み込み、データフレームへ変換
    #         await message.channel.send('ファイル名: '+message.attachments[0].filename + 'を読み込み中だよ')
    #         file = await message.attachments[0].read()
    #         df_new = pd.read_csv(BytesIO(file))
            
    #         # 処理
    #         modifyRole(message,df_new)

    #     # 例外。memo: ファイルなしの呼び出しはgetroleにしてもいいかも。
    #     else:
    #         await message.channel.send('添付ファイルが無いか、添付ファイルが複数だよ')


###########################################################################################
# 以下、新たに定義した関数。別pyファイルに移行するかも。
###########################################################################################

# $getrole を読んだときに実行する処理
# 現在のロール状況をデータフレームとして取得する
def getRole(message):
    members = message.channel.guild.members
    roles = message.channel.guild.roles
    
    # ロールのリストを作成→ヘッダー行を作成
    rolesNameList = []
    for r in roles:
        rolesNameList.append(r.name)
    header = ['id','name'] + rolesNameList

    # データフレーム作成用の配列を作成、ヘッダー行を追加
    dfRows = []

    # ヘッダー以下の行を作成。各メンバーに対して、id, name, 各ロールを持つ/持たないの値からなるリストを作成し、二次元配列として次々追加
    for m in members:
        
        # 現在のループ用のリストを作成
        curRolesList = [m.id, m.name + '#' + m.discriminator]
        
        # 各ロールに対して、持つ/持たないの値を追加
        for r in roles:
            curRolesList.append(r in m.roles)
        
        # データフレーム作成用の二次元配列に追加     
        dfRows.append(curRolesList)

    # pdデータフレーム作成
    df = pd.DataFrame(dfRows)
    df.columns = header
    
    return df


# $ggRoleを読んだときに実行する処理

def ggRole(message,df,role):
    # 1. ggのcsvに乗ってる人を特定する
    # join discord...がヘッダーの列を特定する
    for e in df.columns:
        if str(e).startswith('Join https://discord.gg/'):
            break
        
    # discordの列番号を取得
    targetIndex = df.columns.tolist().index(e)
    
    # join discord の列を取得
    ggNameList = df.iloc[:,targetIndex].to_list()
    # print(ggNameList)
     
    # 2. Discordサーバーメンバーを取得する
    df_server = getRole(message)
    serverNameJson = json.loads(df_server.loc[:,['id','name']].to_json())

    # print(serverNameJson)

    # 3. それぞれcsv上の各メンバーがに対し、Discord上に存在していればロールを付与、そうでなければエラーログリストに追加
    targetMemberList = []
    notFoundsList = []

    for e in ggNameList:
        if e in serverNameJson['name'].values():
            # discord id取得, リストへ追加
            print(e)
            try:
                print(df_server[df_server['name'].isin([e])])
                cur_index = df_server.index[df_server['name'] == e].tolist()
                print(cur_index)
                print('cur_index: ' + str(cur_index[0]))
                print(e + ':' + str(df_server[df_server['name'].isin([e])].at[cur_index[0],'id']))
                targetMemberList.append(df_server[df_server['name'].isin([e])].at[cur_index[0],'id'])
            except KeyError:
                print('なんかエラった！！！！')
        else:
            notFoundsList.append(e)
            print(str(e) + 'はサーバーにいないよ')

    out = {'targetMemberList':targetMemberList, 'notFoundsList': notFoundsList}
    print(out)
    
    # 4. 処理完了ログを送出する
    return out


client.run(TOKEN) 


###########################################################################
###############
# 開発一時停止 #
###############

# $modifyroleを読んだときに実行する処理
# 送信したCSVの通りにロールを振りなおす

# アウトライン
# 現在のロール（旧）とアップロードしたロール（新）を見比べて、違うところがあったらアップした方に合わせて修正する
# ロールが増えたり減ったり名前が変わってたりしたらエラーを吐く

# 例外処理
# 新旧（Old/New）ヘッダー列を見比べて、ロールリストに更新があったらエラーを吐いて止まる
# if headerO == headerN:

# メンバーの過不足に対しては処理を止めず、ロールを振れなかった人のログとして吐き出す
# (1) OにいるがNにいない場合、退出したか名前が変わっている人。setO - setN
# (2) NにいるがOにいない場合、新しく参加したか名前が変わっている人。setN - setO
# (3) (!),(2)の両方にいてDiscriminatorが同じな場合、名前が変わっている人setO & set N
    # ログ送出：
    # 退出した？setO - setN
    # 参加した？setN - setO
    # 名前変わった？setO & setN

# 処理方法
# 差異がある参加者に対しては行削除を行い、データフレームの形を合わせる.
    # どっちかにだけいる人 setO ^ setN のidの列をデータフレームから削除する
# 各メンバーに対して各ロールのT/Fを比較し、旧T新Fならremove_role, 旧F新Tならadd_roleする
# 論理値の処理としてスマートにできないか？
# dfOとdfNのXORを取る。dfNのうちXORがTの部分に対して、dfNの値になるようロールを振る
# 

# def modifyRole(message,df_new):

#     # 現在のロール状況を取得
#     df_old = getRole(message)

    
#     return