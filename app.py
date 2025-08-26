from app import create_app
import os
app = create_app()

if __name__ == '__main__':
    #app.run(debug=True, host='0.0.0.0', port=5000)

    PORT = os.getenv('CDSW_READONLY_PORT', '8090')
    app.run(host="127.0.0.1", port=int(PORT))