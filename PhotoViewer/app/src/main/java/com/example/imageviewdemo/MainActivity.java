package com.example.imageviewdemo;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.view.View;
import android.webkit.MimeTypeMap;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {
    private static final int MY_PERMISSIONS_REQUEST_WRITE_EXTERNAL_STORAGE = 1;
    ImageView imgView;
    TextView textView;
    String site_url = "http://10.0.2.2:8000";
    //String site_url = "https://ny8082.pythonanywhere.com";
    JSONObject post_json;
    String imageUrl = null;
    Bitmap bmImg = null;
    CloadImage taskDownload;
    PutPost taskUpload;

    Uri imageUri = null;    // 업로드할 이미지
    ImageView imgPreview;

    // 이미지 파일 선택
    ActivityResultLauncher<String> imagePicker = registerForActivityResult(
            new ActivityResultContracts.GetContent(),
            uri -> {
                if (uri != null) {
                    imageUri = uri;
                    imgPreview.setImageURI(uri);
                }
            });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        //imgView = (ImageView) findViewById(R.id.imgView);
        textView = (TextView)findViewById(R.id.textView);
    }

    public void onClickDownload(View v) {
        if (taskDownload != null && taskDownload.getStatus() == AsyncTask.Status.RUNNING) {
            taskDownload.cancel(true);
        }
        taskDownload = new CloadImage();
        taskDownload.execute(site_url + "/api_root/Post/");
        Toast.makeText(getApplicationContext(), "Download", Toast.LENGTH_LONG).show();
    }

    public void onClickUpload(View v) {
        View dialogView = getLayoutInflater().inflate(R.layout.dialog_upload, null);
        EditText editTitle = dialogView.findViewById(R.id.editTitle);
        EditText editText = dialogView.findViewById(R.id.editText);
        Button btnImage = dialogView.findViewById(R.id.btn_image);
        imgPreview = dialogView.findViewById(R.id.imgPreview);
        imageUri = null;

        btnImage.setOnClickListener(view -> imagePicker.launch("image/*"));

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("새로운 이미지 게시")
                .setView(dialogView)
                .setPositiveButton("게시", null)
                .setNegativeButton("취소", null)
                .create();
        dialog.show();

        // 입력이 빠졌으면 창을 닫지 않고 알려줌
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
            String title = editTitle.getText().toString();
            String text = editText.getText().toString();
            if (title.isEmpty() || text.isEmpty() || imageUri == null) {
                Toast.makeText(getApplicationContext(), "제목, 내용, 이미지를 모두 입력하세요", Toast.LENGTH_SHORT).show();
                return;
            }
            dialog.dismiss();

            taskUpload = new PutPost(title, text, imageUri);
            taskUpload.execute(site_url + "/api_root/Post/");
            Toast.makeText(getApplicationContext(), "Upload", Toast.LENGTH_LONG).show();
        });
    }

    private class CloadImage extends AsyncTask<String, Integer, List<Bitmap>> {
        @Override
        protected List<Bitmap> doInBackground(String... urls) {
            List<Bitmap> bitmapList = new ArrayList<>();
            try {
                String apiUrl = urls[0];
                String token = "88f92f3b48b19a9f46b2728b828b806fb26e53de";
                URL urlAPI = new URL(apiUrl);
                HttpURLConnection conn = (HttpURLConnection) urlAPI.openConnection();
                conn.setRequestProperty("Authorization", "Token " + token);
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(3000);

                int responseCode = conn.getResponseCode();
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    InputStream is = conn.getInputStream();
                    BufferedReader reader = new BufferedReader(new InputStreamReader(is));
                    StringBuilder result = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        result.append(line);
                    }
                    is.close();

                    String strJson = result.toString();
                    JSONArray aryJson = new JSONArray(strJson);
                    // 배열 내 모든 이미지 다운로드
                    for (int i = 0; i < aryJson.length(); i++) {
                        post_json = (JSONObject) aryJson.get(i);
                        imageUrl = post_json.getString("image");
                        if (!imageUrl.equals("")) {
                            URL myImageUrl = new URL(imageUrl);
                            conn = (HttpURLConnection) myImageUrl.openConnection();
                            InputStream imgStream = conn.getInputStream();

                            Bitmap imageBitmap = BitmapFactory.decodeStream(imgStream);
                            bitmapList.add(imageBitmap); // 이미지 리스트에 추가
                            imgStream.close();
                        }
                    }
                }
            } catch (IOException | JSONException e) {
                e.printStackTrace();
            }
            return bitmapList;
        }

        @Override
        protected void onPostExecute(List<Bitmap> images) {
            if (images.isEmpty()) {
                textView.setText("불러올 이미지가 없습니다.");
            } else {
                textView.setText("이미지 로드 성공!");
                RecyclerView recyclerView = findViewById(R.id.recyclerView);
                ImageAdapter adapter = new ImageAdapter(images);
                recyclerView.setLayoutManager(new LinearLayoutManager(MainActivity.this));
                recyclerView.setAdapter(adapter);
            }
        }
    }

    private class PutPost extends AsyncTask<String, Void, Void> {
        String title;
        String text;
        Uri uri;
        int responseCode = 0;

        PutPost(String title, String text, Uri uri) {
            this.title = title;
            this.text = text;
            this.uri = uri;
        }

        @Override
        protected Void doInBackground(String... urls) {
            String boundary = "----PhotoViewer" + System.currentTimeMillis();
            try {
                String apiUrl = urls[0];
                String token = "88f92f3b48b19a9f46b2728b828b806fb26e53de";
                URL urlAPI = new URL(apiUrl);
                HttpURLConnection conn = (HttpURLConnection) urlAPI.openConnection();
                conn.setRequestProperty("Authorization", "Token " + token);
                conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
                conn.setRequestMethod("POST");
                conn.setDoOutput(true);
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(10000);

                // 작성 시각 (예: 2024-06-03T18:34:00+09:00)
                String now = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.KOREA).format(new Date());

                // 이미지 종류에 맞춰 파일 이름 만들기
                String mimeType = getContentResolver().getType(uri);
                String ext = MimeTypeMap.getSingleton().getExtensionFromMimeType(mimeType);
                if (ext == null) {
                    ext = "jpg";
                }
                String fileName = "upload_" + System.currentTimeMillis() + "." + ext;

                DataOutputStream dos = new DataOutputStream(conn.getOutputStream());
                writeText(dos, boundary, "author", "1");
                writeText(dos, boundary, "title", title);
                writeText(dos, boundary, "text", text);
                writeText(dos, boundary, "created_date", now);
                writeText(dos, boundary, "published_date", now);

                // 이미지 파일
                dos.writeBytes("--" + boundary + "\r\n");
                dos.writeBytes("Content-Disposition: form-data; name=\"image\"; filename=\"" + fileName + "\"\r\n");
                dos.writeBytes("Content-Type: " + mimeType + "\r\n");
                dos.writeBytes("\r\n");
                InputStream is = getContentResolver().openInputStream(uri);
                byte[] buffer = new byte[4096];
                int len;
                while ((len = is.read(buffer)) != -1) {
                    dos.write(buffer, 0, len);
                }
                is.close();
                dos.writeBytes("\r\n");
                dos.writeBytes("--" + boundary + "--\r\n");
                dos.flush();
                dos.close();

                responseCode = conn.getResponseCode();
            } catch (IOException e) {
                e.printStackTrace();
            }
            return null;
        }

        @Override
        protected void onPostExecute(Void unused) {
            if (responseCode == HttpURLConnection.HTTP_CREATED) {
                Toast.makeText(getApplicationContext(), "업로드 성공!", Toast.LENGTH_LONG).show();
                // 올린 이미지까지 목록 다시 불러오기
                taskDownload = new CloadImage();
                taskDownload.execute(site_url + "/api_root/Post/");
            } else {
                Toast.makeText(getApplicationContext(), "업로드 실패 (" + responseCode + ")", Toast.LENGTH_LONG).show();
            }
        }
    }

    // multipart 텍스트 항목 하나 쓰기
    private void writeText(DataOutputStream dos, String boundary, String name, String value) throws IOException {
        dos.writeBytes("--" + boundary + "\r\n");
        dos.writeBytes("Content-Disposition: form-data; name=\"" + name + "\"\r\n");
        dos.writeBytes("\r\n");
        dos.write(value.getBytes("UTF-8"));
        dos.writeBytes("\r\n");
    }
}
