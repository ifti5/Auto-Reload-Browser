import html
import os
import queue
import re
import shutil
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


SETTINGS_GRADLE = r'''
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "__PROJECT_NAME__"
include(":app")
'''.strip()


ROOT_BUILD_GRADLE = r'''
plugins {
    id("com.android.application") version "8.7.3" apply false
}
'''.strip()


GRADLE_PROPERTIES = r'''
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=false
android.nonTransitiveRClass=true
android.enableR8.fullMode=true
'''.strip()


APP_BUILD_GRADLE = r'''
plugins {
    id("com.android.application")
}

android {
    namespace = "__PACKAGE_NAME__"
    compileSdk = 35

    defaultConfig {
        applicationId = "__PACKAGE_NAME__"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        debug {
            minifyEnabled = false
        }

        release {
            minifyEnabled = true
            shrinkResources = true

            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
'''.strip()


MANIFEST_XML = r'''
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>

    <application
        android:allowBackup="false"
        android:hardwareAccelerated="true"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="true"
        android:enableOnBackInvokedCallback="false">

        <activity
            android:name=".MainActivity"
            android:configChanges="keyboardHidden|orientation|screenSize"
            android:exported="true">

            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>

        </activity>

    </application>

</manifest>
'''.strip()


STYLES_XML = r'''
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="@android:style/Theme.Material.Light.NoActionBar">
        <item name="android:windowNoTitle">true</item>
        <item name="android:windowFullscreen">true</item>
        <item name="android:windowActionModeOverlay">true</item>
        <item name="android:windowBackground">#081A2B</item>
        <item name="android:fontFamily">sans</item>
        <item name="android:colorAccent">#16A085</item>
        <item name="android:statusBarColor">#081A2B</item>
        <item name="android:navigationBarColor">#081A2B</item>
    </style>
</resources>
'''.strip()


PROGUARD_RULES = r'''
# No custom rules are required for the standard Android WebView APIs.
'''.strip()


MAIN_ACTIVITY_JAVA = r'''
package __PACKAGE_NAME__;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.webkit.CookieManager;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private final Handler reloadHandler = new Handler(Looper.getMainLooper());

    private WebView webView;
    private boolean browserOpen = false;

    private String currentUrl = "";
    private long reloadInterval = 5000L;

    private final Runnable reloadRunnable = new Runnable() {
        @Override
        public void run() {
            if (browserOpen && webView != null && !isFinishing()) {
                webView.reload();
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        enableImmersiveMode();
        showSetupScreen();
    }

    private void showSetupScreen() {
        browserOpen = false;
        reloadHandler.removeCallbacks(reloadRunnable);
        destroyWebView();

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(8, 26, 43));

        ScrollView scrollView = new ScrollView(this);
        scrollView.setFillViewport(true);
        scrollView.setOverScrollMode(View.OVER_SCROLL_NEVER);

        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setGravity(Gravity.CENTER);
        page.setPadding(dp(24), dp(32), dp(24), dp(32));

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setGravity(Gravity.CENTER_HORIZONTAL);
        card.setPadding(dp(24), dp(28), dp(24), dp(28));
        card.setBackground(roundedBackground(Color.WHITE, 22));
        card.setElevation(dp(10));

        TextView title = new TextView(this);
        title.setText("__APP_NAME_JAVA__");
        title.setTextSize(25);
        title.setTextColor(Color.rgb(8, 26, 43));
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        title.setGravity(Gravity.CENTER);

        TextView subtitle = new TextView(this);
        subtitle.setText("Enter a website and an automatic reload interval.");
        subtitle.setTextSize(14);
        subtitle.setTextColor(Color.rgb(90, 108, 120));
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setPadding(0, dp(8), 0, dp(24));

        TextView urlLabel = createLabel("Website URL");

        EditText urlInput = createInput();
        urlInput.setHint("https://example.com");
        urlInput.setText(currentUrl);
        urlInput.setSingleLine(true);
        urlInput.setInputType(
            InputType.TYPE_CLASS_TEXT |
            InputType.TYPE_TEXT_VARIATION_URI
        );
        urlInput.setImeOptions(EditorInfo.IME_ACTION_NEXT);

        TextView intervalLabel = createLabel("Reload interval in milliseconds");

        EditText intervalInput = createInput();
        intervalInput.setHint("5000");
        intervalInput.setText(String.valueOf(reloadInterval));
        intervalInput.setSingleLine(true);
        intervalInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        intervalInput.setImeOptions(EditorInfo.IME_ACTION_DONE);

        TextView help = new TextView(this);
        help.setText("1000 = 1 second, 60000 = 1 minute");
        help.setTextSize(12);
        help.setTextColor(Color.rgb(112, 127, 136));
        help.setPadding(dp(2), dp(7), dp(2), dp(20));

        Button startButton = new Button(this);
        startButton.setText("OPEN FULL-SCREEN BROWSER");
        startButton.setTextSize(14);
        startButton.setTextColor(Color.WHITE);
        startButton.setAllCaps(false);
        startButton.setStateListAnimator(null);
        startButton.setBackground(
            roundedBackground(Color.rgb(22, 160, 133), 12)
        );

        TextView footer = new TextView(this);
        footer.setText(
            "Press Android Back while browsing to return to these settings."
        );
        footer.setTextSize(12);
        footer.setTextColor(Color.rgb(121, 135, 143));
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(dp(4), dp(20), dp(4), 0);

        View.OnClickListener submitListener = view -> {
            urlInput.setError(null);
            intervalInput.setError(null);

            String url = normalizeUrl(urlInput.getText().toString());
            Long interval = parseInterval(intervalInput.getText().toString());

            boolean valid = true;

            if (url == null) {
                urlInput.setError("Enter a valid HTTP or HTTPS URL");
                valid = false;
            }

            if (interval == null || interval <= 0) {
                intervalInput.setError(
                    "Enter an interval greater than zero"
                );
                valid = false;
            }

            if (valid) {
                startBrowser(url, interval);
            }
        };

        startButton.setOnClickListener(submitListener);

        intervalInput.setOnEditorActionListener(
            (view, actionId, event) -> {
                if (actionId == EditorInfo.IME_ACTION_DONE) {
                    startButton.performClick();
                    return true;
                }
                return false;
            }
        );

        card.addView(title, matchWrap());
        card.addView(subtitle, matchWrap());
        card.addView(urlLabel, matchWrap());
        card.addView(urlInput, fieldParams());
        card.addView(intervalLabel, labelParams());
        card.addView(intervalInput, fieldParams());
        card.addView(help, matchWrap());

        card.addView(
            startButton,
            new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(52)
            )
        );

        card.addView(footer, matchWrap());

        int screenWidth = getResources().getDisplayMetrics().widthPixels;
        int cardWidth = Math.min(dp(520), screenWidth - dp(32));

        page.addView(
            card,
            new LinearLayout.LayoutParams(
                cardWidth,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        );

        scrollView.addView(
            page,
            new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        );

        root.addView(
            scrollView,
            new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        );

        setContentView(root);
        enableImmersiveMode();
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void startBrowser(String url, long interval) {
        destroyWebView();
        reloadHandler.removeCallbacks(reloadRunnable);

        currentUrl = url;
        reloadInterval = Math.max(1, interval);
        browserOpen = true;

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.WHITE);
        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);

        WebSettings settings = webView.getSettings();

        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setDefaultTextEncodingName("UTF-8");

        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);

        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setSupportZoom(true);

        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);

        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setMediaPlaybackRequiresUserGesture(true);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            settings.setSafeBrowsingEnabled(true);
        }

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            cookieManager.setAcceptThirdPartyCookies(webView, true);
        }

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(
                WebView view,
                WebResourceRequest request
            ) {
                return handleNavigation(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(
                WebView view,
                String url
            ) {
                return handleNavigation(Uri.parse(url));
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);

                if (browserOpen) {
                    currentUrl = url;
                    scheduleReload();
                }
            }
        });

        root.addView(
            webView,
            new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        );

        setContentView(root);
        enableImmersiveMode();

        webView.loadUrl(currentUrl);

        Toast.makeText(
            this,
            "Press Back to change the URL or interval",
            Toast.LENGTH_SHORT
        ).show();
    }

    private void scheduleReload() {
        reloadHandler.removeCallbacks(reloadRunnable);

        if (browserOpen && webView != null && !isFinishing()) {
            reloadHandler.postDelayed(
                reloadRunnable,
                reloadInterval
            );
        }
    }

    private boolean handleNavigation(Uri uri) {
        String scheme = uri.getScheme();

        if (
            scheme == null ||
            scheme.equalsIgnoreCase("http") ||
            scheme.equalsIgnoreCase("https")
        ) {
            return false;
        }

        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (ActivityNotFoundException exception) {
            Toast.makeText(
                this,
                "No installed application can open this link.",
                Toast.LENGTH_SHORT
            ).show();
        }

        return true;
    }

    private String normalizeUrl(String rawValue) {
        String value = rawValue == null ? "" : rawValue.trim();

        if (value.isEmpty()) {
            return null;
        }

        String candidate;

        if (
            value.toLowerCase().startsWith("http://") ||
            value.toLowerCase().startsWith("https://")
        ) {
            candidate = value;
        } else {
            candidate = "https://" + value;
        }

        try {
            Uri uri = Uri.parse(candidate);
            String scheme = uri.getScheme();
            String host = uri.getHost();

            if (
                scheme != null &&
                host != null &&
                !host.trim().isEmpty() &&
                (
                    scheme.equalsIgnoreCase("http") ||
                    scheme.equalsIgnoreCase("https")
                )
            ) {
                return candidate;
            }
        } catch (Exception ignored) {
        }

        return null;
    }

    private Long parseInterval(String value) {
        try {
            return Long.parseLong(value.trim());
        } catch (Exception exception) {
            return null;
        }
    }

    private void enableImmersiveMode() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().setDecorFitsSystemWindows(false);

            WindowInsetsController controller =
                getWindow().getInsetsController();

            if (controller != null) {
                controller.hide(
                    WindowInsets.Type.statusBars() |
                    WindowInsets.Type.navigationBars()
                );

                controller.setSystemBarsBehavior(
                    WindowInsetsController
                        .BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                );
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
                View.SYSTEM_UI_FLAG_FULLSCREEN |
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            );
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);

        if (hasFocus) {
            enableImmersiveMode();
        }
    }

    @Override
    public void onBackPressed() {
        if (browserOpen) {
            showSetupScreen();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        reloadHandler.removeCallbacks(reloadRunnable);

        if (webView != null) {
            webView.onPause();
        }

        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        enableImmersiveMode();

        if (webView != null) {
            webView.onResume();
        }

        if (browserOpen) {
            scheduleReload();
        }
    }

    @Override
    protected void onDestroy() {
        reloadHandler.removeCallbacksAndMessages(null);
        destroyWebView();
        super.onDestroy();
    }

    private void destroyWebView() {
        if (webView != null) {
            webView.stopLoading();
            webView.loadUrl("about:blank");
            webView.clearHistory();
            webView.removeAllViews();
            webView.destroy();
            webView = null;
        }
    }

    private TextView createLabel(String value) {
        TextView label = new TextView(this);
        label.setText(value);
        label.setTextSize(13);
        label.setTextColor(Color.rgb(46, 65, 75));
        label.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return label;
    }

    private EditText createInput() {
        EditText input = new EditText(this);
        input.setTextSize(15);
        input.setTextColor(Color.rgb(22, 34, 42));
        input.setHintTextColor(Color.rgb(145, 156, 164));
        input.setPadding(dp(14), dp(12), dp(14), dp(12));

        GradientDrawable background = new GradientDrawable();
        background.setShape(GradientDrawable.RECTANGLE);
        background.setColor(Color.rgb(248, 250, 252));
        background.setCornerRadius(dp(11));
        background.setStroke(dp(1), Color.rgb(210, 219, 226));

        input.setBackground(background);
        return input;
    }

    private GradientDrawable roundedBackground(
        int color,
        int radius
    ) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setShape(GradientDrawable.RECTANGLE);
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radius));
        return drawable;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        );
    }

    private LinearLayout.LayoutParams labelParams() {
        LinearLayout.LayoutParams params = matchWrap();
        params.topMargin = dp(18);
        return params;
    }

    private LinearLayout.LayoutParams fieldParams() {
        LinearLayout.LayoutParams params =
            new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(52)
            );

        params.topMargin = dp(7);
        return params;
    }

    private int dp(int value) {
        return (int) (
            value * getResources().getDisplayMetrics().density
        );
    }
}
'''.strip()


class APKBuilderGUI:
    PACKAGE_PATTERN = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$"
    )

    def __init__(self, root):
        self.root = root
        self.root.title("Auto Reload Browser APK Builder")
        self.root.geometry("820x700")
        self.root.minsize(700, 600)

        self.log_queue = queue.Queue()
        self.building = False

        default_gradle = (
            shutil.which("gradle")
            or shutil.which("gradle.bat")
            or ""
        )

        default_sdk = (
            os.environ.get("ANDROID_SDK_ROOT")
            or os.environ.get("ANDROID_HOME")
            or self.detect_android_sdk()
            or ""
        )

        self.app_name = tk.StringVar(value="Auto Reload Browser")
        self.package_name = tk.StringVar(
            value="com.example.autoreloadbrowser"
        )
        self.project_folder = tk.StringVar(
            value=str(Path.cwd() / "GeneratedBrowserApp")
        )
        self.sdk_folder = tk.StringVar(value=default_sdk)
        self.gradle_executable = tk.StringVar(value=default_gradle)

        self.create_widgets()
        self.root.after(100, self.process_log_queue)

    @staticmethod
    def detect_android_sdk():
        home = Path.home()

        candidates = [
            home / "AppData" / "Local" / "Android" / "Sdk",
            home / "Library" / "Android" / "sdk",
            home / "Android" / "Sdk",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return ""

    def create_widgets(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(
            outer,
            text="Auto Reload Browser APK Builder",
            font=("TkDefaultFont", 18, "bold")
        )
        title.pack(anchor="w", pady=(0, 6))

        description = ttk.Label(
            outer,
            text=(
                "This tool generates a native Android WebView project and "
                "builds an installable debug APK."
            ),
            wraplength=760
        )
        description.pack(anchor="w", pady=(0, 18))

        form = ttk.Frame(outer)
        form.pack(fill="x")

        self.add_entry(
            form,
            0,
            "Application name",
            self.app_name
        )

        self.add_entry(
            form,
            1,
            "Android package",
            self.package_name
        )

        self.add_path_entry(
            form,
            2,
            "Project folder",
            self.project_folder,
            self.select_project_folder,
            "Browse"
        )

        self.add_path_entry(
            form,
            3,
            "Android SDK folder",
            self.sdk_folder,
            self.select_sdk_folder,
            "Browse"
        )

        self.add_path_entry(
            form,
            4,
            "Gradle executable",
            self.gradle_executable,
            self.select_gradle,
            "Browse"
        )

        button_frame = ttk.Frame(outer)
        button_frame.pack(fill="x", pady=(18, 12))

        self.build_button = ttk.Button(
            button_frame,
            text="Generate Project and Build APK",
            command=self.start_build
        )
        self.build_button.pack(side="left")

        ttk.Button(
            button_frame,
            text="Open Project Folder",
            command=self.open_project_folder
        ).pack(side="left", padx=(10, 0))

        self.progress = ttk.Progressbar(
            button_frame,
            mode="indeterminate",
            length=180
        )
        self.progress.pack(side="right")

        ttk.Label(
            outer,
            text="Build output",
            font=("TkDefaultFont", 11, "bold")
        ).pack(anchor="w")

        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True, pady=(6, 0))

        self.log_widget = tk.Text(
            log_frame,
            wrap="word",
            height=20,
            background="#101820",
            foreground="#E8F0F2",
            insertbackground="white"
        )
        self.log_widget.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log_widget.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.log_widget.configure(yscrollcommand=scrollbar.set)

        self.log(
            "Ready.\n"
            "Make sure JDK 17, Android SDK Platform 35, and Gradle "
            "are installed.\n"
        )

    @staticmethod
    def add_entry(parent, row, label, variable):
        ttk.Label(parent, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7
        )

        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(
            row=row,
            column=1,
            sticky="ew",
            pady=7
        )

        parent.columnconfigure(1, weight=1)

    @staticmethod
    def add_path_entry(
        parent,
        row,
        label,
        variable,
        command,
        button_text
    ):
        ttk.Label(parent, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7
        )

        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(
            row=row,
            column=1,
            sticky="ew",
            pady=7
        )

        ttk.Button(
            parent,
            text=button_text,
            command=command
        ).grid(
            row=row,
            column=2,
            padx=(8, 0),
            pady=7
        )

        parent.columnconfigure(1, weight=1)

    def select_project_folder(self):
        selected = filedialog.askdirectory(
            title="Select project folder"
        )

        if selected:
            self.project_folder.set(selected)

    def select_sdk_folder(self):
        selected = filedialog.askdirectory(
            title="Select Android SDK folder"
        )

        if selected:
            self.sdk_folder.set(selected)

    def select_gradle(self):
        selected = filedialog.askopenfilename(
            title="Select Gradle executable",
            filetypes=[
                ("Executables", "*.exe *.bat *.cmd"),
                ("All files", "*.*")
            ]
        )

        if selected:
            self.gradle_executable.set(selected)

    def open_project_folder(self):
        folder = Path(
            os.path.expandvars(
                os.path.expanduser(
                    self.project_folder.get().strip()
                )
            )
        )

        folder.mkdir(parents=True, exist_ok=True)

        try:
            if os.name == "nt":
                os.startfile(folder)
            elif shutil.which("open"):
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exception:
            messagebox.showerror(
                "Unable to open folder",
                str(exception)
            )

    def validate_inputs(self):
        app_name = self.app_name.get().strip()
        package = self.package_name.get().strip()
        project_text = self.project_folder.get().strip()
        sdk_text = self.sdk_folder.get().strip()
        gradle_text = self.gradle_executable.get().strip()

        if not app_name:
            raise ValueError("Enter an application name.")

        if not self.PACKAGE_PATTERN.fullmatch(package):
            raise ValueError(
                "Enter a valid package such as "
                "com.example.autoreloadbrowser."
            )

        if not project_text:
            raise ValueError("Select a project folder.")

        if not sdk_text:
            raise ValueError("Select the Android SDK folder.")

        sdk = Path(
            os.path.expandvars(
                os.path.expanduser(sdk_text)
            )
        )

        if not sdk.exists():
            raise ValueError(
                f"Android SDK folder does not exist:\n{sdk}"
            )

        if not gradle_text:
            raise ValueError(
                "Select the Gradle executable or add Gradle to PATH."
            )

        if (
            os.path.sep in gradle_text
            or "/" in gradle_text
            or "\\" in gradle_text
        ):
            gradle_path = Path(
                os.path.expandvars(
                    os.path.expanduser(gradle_text)
                )
            )

            if not gradle_path.exists():
                raise ValueError(
                    f"Gradle executable does not exist:\n{gradle_path}"
                )

        return {
            "app_name": app_name,
            "package": package,
            "project": Path(
                os.path.expandvars(
                    os.path.expanduser(project_text)
                )
            ),
            "sdk": sdk,
            "gradle": gradle_text,
        }

    def start_build(self):
        if self.building:
            return

        try:
            configuration = self.validate_inputs()
        except ValueError as exception:
            messagebox.showerror("Invalid configuration", str(exception))
            return

        self.building = True
        self.build_button.configure(state="disabled")
        self.progress.start(10)

        self.log("\n" + "=" * 64 + "\n")
        self.log("Starting build...\n")

        worker = threading.Thread(
            target=self.build_project,
            args=(configuration,),
            daemon=True
        )
        worker.start()

    def build_project(self, configuration):
        try:
            project = configuration["project"]
            sdk = configuration["sdk"]
            gradle = configuration["gradle"]
            package = configuration["package"]
            app_name = configuration["app_name"]

            self.thread_log(f"Project folder: {project}\n")
            self.thread_log(f"Android SDK: {sdk}\n")
            self.thread_log(f"Package: {package}\n")

            self.generate_project(
                project=project,
                sdk=sdk,
                package=package,
                app_name=app_name
            )

            self.thread_log("Android project generated.\n")
            self.thread_log("Checking Gradle...\n")

            self.run_process(
                [gradle, "--version"],
                cwd=project,
                sdk=sdk
            )

            self.thread_log("\nBuilding debug APK...\n")

            self.run_process(
                [
                    gradle,
                    "--no-daemon",
                    "--stacktrace",
                    "assembleDebug"
                ],
                cwd=project,
                sdk=sdk
            )

            source_apk = (
                project
                / "app"
                / "build"
                / "outputs"
                / "apk"
                / "debug"
                / "app-debug.apk"
            )

            if not source_apk.exists():
                raise RuntimeError(
                    "Gradle completed but app-debug.apk was not found."
                )

            safe_name = re.sub(
                r"[^a-zA-Z0-9._-]+",
                "_",
                app_name
            ).strip("_")

            if not safe_name:
                safe_name = "AutoReloadBrowser"

            destination = project / f"{safe_name}-debug.apk"
            shutil.copy2(source_apk, destination)

            self.thread_log("\nBUILD SUCCESSFUL\n")
            self.thread_log(f"APK created at:\n{destination}\n")

            self.log_queue.put(
                (
                    "success",
                    str(destination)
                )
            )

        except Exception as exception:
            self.thread_log(f"\nBUILD FAILED\n{exception}\n")
            self.log_queue.put(("error", str(exception)))
        finally:
            self.log_queue.put(("finished", None))

    def generate_project(
        self,
        project,
        sdk,
        package,
        app_name
    ):
        java_folder = (
            project
            / "app"
            / "src"
            / "main"
            / "java"
            / Path(*package.split("."))
        )

        values_folder = (
            project
            / "app"
            / "src"
            / "main"
            / "res"
            / "values"
        )

        java_folder.mkdir(parents=True, exist_ok=True)
        values_folder.mkdir(parents=True, exist_ok=True)

        project_name = re.sub(
            r"[^a-zA-Z0-9_-]",
            "",
            app_name.replace(" ", "")
        ) or "AutoReloadBrowser"

        settings = SETTINGS_GRADLE.replace(
            "__PROJECT_NAME__",
            project_name
        )

        app_gradle = APP_BUILD_GRADLE.replace(
            "__PACKAGE_NAME__",
            package
        )

        java_app_name = (
            app_name
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", " ")
            .replace("\r", " ")
        )

        main_activity = (
            MAIN_ACTIVITY_JAVA
            .replace("__PACKAGE_NAME__", package)
            .replace("__APP_NAME_JAVA__", java_app_name)
        )

        strings_xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<resources>\n"
            f'    <string name="app_name">'
            f"{html.escape(app_name)}"
            "</string>\n"
            "</resources>\n"
        )

        sdk_path = str(sdk.resolve()).replace("\\", "\\\\")
        local_properties = f"sdk.dir={sdk_path}\n"

        files = {
            project / "settings.gradle.kts": settings,
            project / "build.gradle.kts": ROOT_BUILD_GRADLE,
            project / "gradle.properties": GRADLE_PROPERTIES,
            project / "local.properties": local_properties,
            project / "app" / "build.gradle.kts": app_gradle,
            project / "app" / "proguard-rules.pro": PROGUARD_RULES,
            (
                project / "app" / "src" / "main"
                / "AndroidManifest.xml"
            ): MANIFEST_XML,
            values_folder / "styles.xml": STYLES_XML,
            values_folder / "strings.xml": strings_xml,
            java_folder / "MainActivity.java": main_activity,
        }

        for file_path, content in files.items():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                content + "\n",
                encoding="utf-8"
            )
            self.thread_log(f"Created: {file_path}\n")

    def run_process(self, command, cwd, sdk):
        environment = os.environ.copy()
        environment["ANDROID_SDK_ROOT"] = str(sdk)
        environment["ANDROID_HOME"] = str(sdk)

        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False
        )

        if process.stdout is not None:
            for line in process.stdout:
                self.thread_log(line)

        return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(
                f"Command exited with code {return_code}: "
                + " ".join(command)
            )

    def thread_log(self, text):
        self.log_queue.put(("log", text))

    def log(self, text):
        self.log_widget.insert("end", text)
        self.log_widget.see("end")

    def process_log_queue(self):
        try:
            while True:
                event, value = self.log_queue.get_nowait()

                if event == "log":
                    self.log(value)

                elif event == "success":
                    messagebox.showinfo(
                        "APK created",
                        "The APK was created successfully:\n\n"
                        + value
                    )

                elif event == "error":
                    messagebox.showerror(
                        "Build failed",
                        value
                    )

                elif event == "finished":
                    self.building = False
                    self.build_button.configure(state="normal")
                    self.progress.stop()

        except queue.Empty:
            pass

        self.root.after(100, self.process_log_queue)


def main():
    root = tk.Tk()

    try:
        style = ttk.Style(root)

        if "clam" in style.theme_names():
            style.theme_use("clam")
    except tk.TclError:
        pass

    APKBuilderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
