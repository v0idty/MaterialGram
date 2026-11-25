#!/usr/bin/env python3
"""Prepare the pinned Telegram Android submodule for a MaterialGram debug build.

Secrets are injected only into the ephemeral GitHub Actions checkout. This script
never prints API credentials and never writes them back to the parent repository.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream" / "Telegram-Android"
PACKAGE = "org.materialgram"


def fail(message: str) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Required upstream file is missing: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def replace_line(content: str, pattern: str, replacement: str, description: str) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count == 1:
        return updated
    if re.search(re.escape(replacement), content):
        return content
    fail(f"Could not find the expected {description} setting in the pinned upstream source")


def set_java_value(content: str, field: str, value: str) -> str:
    pattern = rf'(?m)^(\s*public static (?:int|boolean|String) {re.escape(field)} = ).*?;'
    updated, count = re.subn(pattern, lambda m: m.group(1) + value + ";", content, count=1)
    if count != 1:
        fail(f"Could not safely patch BuildVars.{field}")
    return updated


def replace_once(content: str, old: str, new: str, description: str) -> str:
    count = content.count(old)
    if count != 1:
        fail(f"Could not safely patch {description}: expected one match, found {count}.")
    return content.replace(old, new, 1)


def patch_materialgram_features() -> None:
    """Patch the pinned Telegram UI with MaterialGram's optional adaptive navigation.

    The native Telegram tab capsule always stays on screen. The MaterialGram
    switch only toggles the extras: the search button and the collapse-on-scroll
    behaviour (only the selected tab stays expanded while the chat list scrolls down).
    """
    ui_root = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui"

    settings_helper = ui_root / "MaterialGramSettings.java"
    write_text(settings_helper, """package org.telegram.ui;

import android.content.Context;
import android.content.SharedPreferences;
import org.telegram.messenger.ApplicationLoader;

/** Preferences owned by the MaterialGram fork. */
public final class MaterialGramSettings {
    private static final String PREFERENCES = "materialgram_settings";
    private static final String KEY_BOTTOM_NAVIGATION = "bottom_navigation_enabled";
    private static final String KEY_AVATAR_SHAPE = "avatar_shape";
    private static final String KEY_MATERIAL_INPUT = "material_input";
    private static final String KEY_MATERIAL_VOICE = "material_voice";
    private static final String KEY_APP_COLOR = "app_color";
    private static volatile int cachedAvatarShape = -1;

    private MaterialGramSettings() {
    }

    private static SharedPreferences prefs() {
        final Context context = ApplicationLoader.applicationContext;
        return context == null ? null : context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE);
    }

    public static boolean isBottomNavigationEnabled() {
        final SharedPreferences p = prefs();
        return p == null || p.getBoolean(KEY_BOTTOM_NAVIGATION, true);
    }

    public static void setBottomNavigationEnabled(boolean enabled) {
        final SharedPreferences p = prefs();
        if (p != null) {
            p.edit().putBoolean(KEY_BOTTOM_NAVIGATION, enabled).apply();
        }
    }

    /** Material You shaped mic / send buttons in the chat input panel. Off by default. */
    public static boolean isMaterialInputEnabled() {
        final SharedPreferences p = prefs();
        return p != null && p.getBoolean(KEY_MATERIAL_INPUT, false);
    }

    public static void setMaterialInputEnabled(boolean enabled) {
        final SharedPreferences p = prefs();
        if (p != null) {
            p.edit().putBoolean(KEY_MATERIAL_INPUT, enabled).apply();
        }
    }

    /** 0 blue (Telegram default), 1 green, 2 pink. */
    public static int getAppColor() {
        final SharedPreferences p = prefs();
        final int value = p == null ? 0 : p.getInt(KEY_APP_COLOR, 0);
        return value >= 0 && value < MaterialGramThemeColors.COUNT ? value : 0;
    }

    public static void setAppColor(int color) {
        final SharedPreferences p = prefs();
        if (p != null && color >= 0 && color < MaterialGramThemeColors.COUNT) {
            p.edit().putInt(KEY_APP_COLOR, color).apply();
        }
    }

    /** Material You look of the voice recording panel. Off by default. */
    public static boolean isMaterialVoiceEnabled() {
        final SharedPreferences p = prefs();
        return p != null && p.getBoolean(KEY_MATERIAL_VOICE, false);
    }

    public static void setMaterialVoiceEnabled(boolean enabled) {
        final SharedPreferences p = prefs();
        if (p != null) {
            p.edit().putBoolean(KEY_MATERIAL_VOICE, enabled).apply();
        }
    }

    /** One of MaterialGramShapes.CIRCLE ... MaterialGramShapes.HEART. Local only, never sent anywhere. */
    public static int getAvatarShape() {
        final int cached = cachedAvatarShape;
        if (cached >= 0) {
            return cached;
        }
        final SharedPreferences p = prefs();
        if (p == null) {
            return MaterialGramShapes.CIRCLE;
        }
        final int value = p.getInt(KEY_AVATAR_SHAPE, MaterialGramShapes.CIRCLE);
        final int safe = value >= 0 && value < MaterialGramShapes.COUNT ? value : MaterialGramShapes.CIRCLE;
        cachedAvatarShape = safe;
        return safe;
    }

    public static void setAvatarShape(int shape) {
        final SharedPreferences p = prefs();
        if (p != null && shape >= 0 && shape < MaterialGramShapes.COUNT) {
            cachedAvatarShape = shape;
            p.edit().putInt(KEY_AVATAR_SHAPE, shape).apply();
        }
    }
}
""")

    # Outlines of every selectable avatar shape (pure geometry, no Telegram dependencies).
    write_text(ui_root / "MaterialGramShapes.java", """package org.telegram.ui;

import static org.telegram.messenger.AndroidUtilities.dp;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;

public final class MaterialGramShapes {
    public static final int CIRCLE = 0;
    public static final int ROUNDED = 1;
    public static final int SQUARE = 2;
    public static final int COOKIE = 3;
    public static final int CLOVER = 4;
    public static final int BURST = 5;
    public static final int SUN = 6;
    public static final int PENTAGON = 7;
    public static final int HEXAGON = 8;
    public static final int HEART = 9;
    public static final int COUNT = 10;

    private static final RectF TMP = new RectF();
    private static final ThreadLocal<Path> DRAW_PATH = new ThreadLocal<Path>() {
        @Override
        protected Path initialValue() {
            return new Path();
        }
    };

    private MaterialGramShapes() {
    }

    /**
     * Photo avatars: Telegram draws them as a round rect whose radius is half the size.
     * Draws the chosen shape instead and returns true; returns false (draw normally) for anything else.
     */
    public static boolean drawAvatarRoundRect(Canvas canvas, RectF rect, float radius, Paint paint) {
        final int shape = MaterialGramSettings.getAvatarShape();
        if (shape == CIRCLE || canvas == null) {
            return false;
        }
        final float w = rect.width();
        final float h = rect.height();
        if (w < dp(20) || w > dp(180) || Math.abs(w - h) > 1.5f || radius < w / 2f - 1.5f) {
            return false;
        }
        final Path path = DRAW_PATH.get();
        fillPath(path, shape, rect.left, rect.top, w);
        canvas.drawPath(path, paint);
        return true;
    }

    /** Letter avatars (AvatarDrawable): the canvas is already translated to the avatar's corner. */
    public static boolean drawAvatarCircle(Canvas canvas, float size, Paint paint) {
        final int shape = MaterialGramSettings.getAvatarShape();
        if (shape == CIRCLE || canvas == null || size < dp(20) || size > dp(220)) {
            return false;
        }
        final Path path = DRAW_PATH.get();
        fillPath(path, shape, 0, 0, size);
        canvas.drawPath(path, paint);
        return true;
    }

    /** Writes the outline of the shape into out, fitted into the square (left, top, size). */
    public static void fillPath(Path out, int shape, float left, float top, float size) {
        out.reset();
        final float cx = left + size / 2f;
        final float cy = top + size / 2f;
        final float r = size / 2f;
        switch (shape) {
            case ROUNDED:
                TMP.set(left, top, left + size, top + size);
                out.addRoundRect(TMP, size * 0.3f, size * 0.3f, Path.Direction.CW);
                break;
            case SQUARE:
                TMP.set(left, top, left + size, top + size);
                out.addRoundRect(TMP, size * 0.02f, size * 0.02f, Path.Direction.CW);
                break;
            case COOKIE:
                lobes(out, cx, cy, r, 9, 0.10f, 1f, -90f);
                break;
            case CLOVER:
                lobes(out, cx, cy, r, 4, 0.17f, 1f, 45f);
                break;
            case BURST:
                lobes(out, cx, cy, r, 12, 0.16f, 3f, -90f);
                break;
            case SUN:
                lobes(out, cx, cy, r, 8, 0.15f, 2f, -90f);
                break;
            case PENTAGON:
                polygon(out, cx, cy, r * 0.98f, 5, 0.2f);
                break;
            case HEXAGON:
                polygon(out, cx, cy, r, 6, 0.2f);
                break;
            case HEART:
                heart(out, left, top, size);
                break;
            case CIRCLE:
            default:
                out.addCircle(cx, cy, r, Path.Direction.CW);
                break;
        }
    }

    /** A circle whose radius swells and shrinks n times: cookies, clovers, bursts, suns. */
    private static void lobes(Path out, float cx, float cy, float r, int n, float amp, float sharp, float rotationDeg) {
        final int steps = 360;
        final double rot = Math.toRadians(rotationDeg);
        for (int i = 0; i <= steps; i++) {
            final double theta = Math.PI * 2 * i / steps;
            final double bump = Math.pow((1.0 + Math.cos(n * (theta - rot))) / 2.0, sharp);
            final double radius = r * (1.0 - amp + amp * bump);
            final float x = (float) (cx + radius * Math.cos(theta));
            final float y = (float) (cy + radius * Math.sin(theta));
            if (i == 0) {
                out.moveTo(x, y);
            } else {
                out.lineTo(x, y);
            }
        }
        out.close();
    }

    /** Regular polygon with softly rounded corners. */
    private static void polygon(Path out, float cx, float cy, float r, int n, float corner) {
        final float[] vx = new float[n];
        final float[] vy = new float[n];
        for (int i = 0; i < n; i++) {
            final double a = -Math.PI / 2 + Math.PI * 2 * i / n;
            vx[i] = (float) (cx + r * Math.cos(a));
            vy[i] = (float) (cy + r * Math.sin(a));
        }
        for (int i = 0; i < n; i++) {
            final int prev = (i + n - 1) % n;
            final int next = (i + 1) % n;
            final float p1x = vx[i] + (vx[prev] - vx[i]) * corner;
            final float p1y = vy[i] + (vy[prev] - vy[i]) * corner;
            final float p2x = vx[i] + (vx[next] - vx[i]) * corner;
            final float p2y = vy[i] + (vy[next] - vy[i]) * corner;
            if (i == 0) {
                out.moveTo(p1x, p1y);
            } else {
                out.lineTo(p1x, p1y);
            }
            out.quadTo(vx[i], vy[i], p2x, p2y);
        }
        out.close();
    }

    private static void heart(Path out, float left, float top, float size) {
        out.moveTo(left + size * 0.5f, top + size * 0.92f);
        out.cubicTo(left + size * 0.05f, top + size * 0.58f, left - size * 0.02f, top + size * 0.30f, left + size * 0.18f, top + size * 0.14f);
        out.cubicTo(left + size * 0.33f, top + size * 0.02f, left + size * 0.48f, top + size * 0.12f, left + size * 0.5f, top + size * 0.28f);
        out.cubicTo(left + size * 0.52f, top + size * 0.12f, left + size * 0.67f, top + size * 0.02f, left + size * 0.82f, top + size * 0.14f);
        out.cubicTo(left + size * 1.02f, top + size * 0.30f, left + size * 0.95f, top + size * 0.58f, left + size * 0.5f, top + size * 0.92f);
        out.close();
    }
}
""")

    # Shapes for the chat input panel buttons (Material You style).
    write_text(ui_root / "MaterialGramInputStyle.java", """package org.telegram.ui;

import static org.telegram.messenger.AndroidUtilities.dp;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;

public final class MaterialGramInputStyle {
    private static final ThreadLocal<Path> PATH = new ThreadLocal<Path>() {
        @Override
        protected Path initialValue() {
            return new Path();
        }
    };

    private MaterialGramInputStyle() {
    }

    /**
     * Mic / send button: small corners on the left, big ones on the right.
     * Returns false when the style is off, so the caller draws its usual round button.
     */
    public static boolean drawActionButton(Canvas canvas, RectF rect, Paint paint) {
        if (canvas == null || !MaterialGramSettings.isMaterialInputEnabled()) {
            return false;
        }
        final float big = rect.height() / 2f;
        final float small = Math.min(big, dp(10));
        final Path path = PATH.get();
        path.reset();
        // order: top-left, top-right, bottom-right, bottom-left (x and y each)
        path.addRoundRect(rect, new float[]{small, small, big, big, big, big, small, small}, Path.Direction.CW);
        canvas.drawPath(path, paint);
        return true;
    }
}
""")

    # App colour: picks the matching accent of the light and dark theme and applies it.
    write_text(ui_root / "MaterialGramThemeColors.java", """package org.telegram.ui;

import android.graphics.Color;
import android.view.View;

import org.telegram.ui.ActionBar.Theme;

public final class MaterialGramThemeColors {
    public static final int BLUE = 0;
    public static final int GREEN = 1;
    public static final int PINK = 2;
    public static final int COUNT = 3;

    private static final float[] HUES = {212f, 125f, 335f};

    private MaterialGramThemeColors() {
    }

    /** Accent of the theme closest to the wanted colour; blue is the theme's own default accent. */
    private static Theme.ThemeAccent pick(Theme.ThemeInfo theme, int preset) {
        if (theme == null || theme.themeAccents == null || theme.themeAccents.isEmpty()) {
            return null;
        }
        if (preset == BLUE && theme.themeAccentsMap != null) {
            Theme.ThemeAccent def = theme.themeAccentsMap.get(Theme.DEFALT_THEME_ACCENT_ID);
            if (def == null) {
                def = theme.themeAccentsMap.get(0);
            }
            if (def != null) {
                return def;
            }
        }
        Theme.ThemeAccent best = null;
        float bestDistance = 1000f;
        final float[] hsv = new float[3];
        for (Theme.ThemeAccent accent : theme.themeAccents) {
            Color.colorToHSV(accent.accentColor, hsv);
            if (hsv[1] < 0.3f || hsv[2] < 0.3f) {
                continue;
            }
            float distance = Math.abs(hsv[0] - HUES[preset]);
            distance = Math.min(distance, 360f - distance);
            if (distance < bestDistance) {
                bestDistance = distance;
                best = accent;
            }
        }
        return best;
    }

    private static void applyTo(Theme.ThemeInfo theme, boolean night, int preset, boolean active, View from) {
        final Theme.ThemeAccent accent = pick(theme, preset);
        if (accent == null || theme.currentAccentId == accent.id) {
            return;
        }
        if (active) {
            Theme.switchThemeWithReveal(theme, night, accent.id, from);
        } else {
            theme.setCurrentAccentId(accent.id);
            Theme.saveThemeAccents(theme, true, false, true, false);
        }
    }

    /** Both the light and the dark theme get the colour, so day/night switching stays consistent. */
    public static void apply(int preset, View from) {
        if (preset < 0 || preset >= COUNT) {
            return;
        }
        final Theme.ThemeInfo day = Theme.getCurrentTheme();
        final Theme.ThemeInfo night = Theme.getCurrentNightTheme();
        final boolean nightActive = Theme.isCurrentThemeNight();
        if (day == night) {
            applyTo(day, nightActive, preset, true, from);
            return;
        }
        applyTo(day, false, preset, !nightActive, from);
        applyTo(night, true, preset, nightActive, from);
    }
}
""")

    write_text(ui_root / "MaterialGramColorPickerCell.java", """package org.telegram.ui;

import static org.telegram.messenger.AndroidUtilities.dp;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;
import android.widget.LinearLayout;

import androidx.core.graphics.ColorUtils;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.Theme;

public class MaterialGramColorPickerCell extends LinearLayout {
    public interface Listener {
        void onColorSelected(int preset, View view);
    }

    private static final int[] COLORS = {0xFF3B82F6, 0xFF34A853, 0xFFEC6FA5};
    private static final int[] NAMES = {
        R.string.MaterialGramColorBlue,
        R.string.MaterialGramColorGreen,
        R.string.MaterialGramColorPink
    };

    private final ColorItemView[] items = new ColorItemView[MaterialGramThemeColors.COUNT];
    private Listener listener;

    public MaterialGramColorPickerCell(Context context) {
        super(context);
        setOrientation(HORIZONTAL);
        setPadding(dp(8), dp(8), dp(8), dp(8));
        for (int i = 0; i < items.length; i++) {
            final int preset = i;
            items[i] = new ColorItemView(context, COLORS[i], LocaleController.getString(NAMES[i]));
            items[i].setOnClickListener(v -> {
                setSelected(preset);
                if (listener != null) {
                    listener.onColorSelected(preset, v);
                }
            });
            addView(items[i], new LinearLayout.LayoutParams(0, dp(100), 1f));
        }
    }

    public void setListener(Listener listener) {
        this.listener = listener;
    }

    public void setSelected(int preset) {
        for (int i = 0; i < items.length; i++) {
            items[i].setPicked(i == preset);
        }
    }

    private static class ColorItemView extends View {
        private final int color;
        private final String label;
        private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();
        private boolean picked;

        ColorItemView(Context context, int color, String label) {
            super(context);
            this.color = color;
            this.label = label;
            ring.setStyle(Paint.Style.STROKE);
            ring.setStrokeWidth(dp(3));
            text.setTextSize(dp(13));
            text.setTypeface(AndroidUtilities.bold());
            text.setTextAlign(Paint.Align.CENTER);
        }

        void setPicked(boolean picked) {
            if (this.picked != picked) {
                this.picked = picked;
                invalidate();
            }
        }

        @Override
        protected void onDraw(Canvas canvas) {
            final float w = getWidth();
            final float h = getHeight();
            if (picked) {
                fill.setColor(ColorUtils.setAlphaComponent(color, 40));
                rect.set(dp(6), dp(2), w - dp(6), h - dp(2));
                canvas.drawRoundRect(rect, dp(26), dp(26), fill);
            }
            final float cx = w / 2f;
            final float cy = dp(38);
            fill.setColor(color);
            canvas.drawCircle(cx, cy, dp(22), fill);
            if (picked) {
                ring.setColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
                canvas.drawCircle(cx, cy, dp(27), ring);
            }
            text.setColor(Theme.getColor(picked ? Theme.key_windowBackgroundWhiteBlackText : Theme.key_windowBackgroundWhiteGrayText2));
            canvas.drawText(label, cx, dp(84), text);
        }
    }
}
""")

    # Voice recording look: morphing blob and live waveform.
    write_text(ui_root / "MaterialGramVoiceStyle.java", """package org.telegram.ui;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.os.SystemClock;

public final class MaterialGramVoiceStyle {
    // lobes, amplitude, sharpness of the shapes the blob morphs through
    private static final float[][] SHAPES = {
        {9, 0.10f, 1f},
        {12, 0.16f, 3f},
        {5, 0.14f, 1.5f},
        {8, 0.15f, 2f},
        {4, 0.17f, 1f}
    };
    private static final long HOLD_MS = 700;
    private static final long MORPH_MS = 450;
    private static final Path BLOB = new Path();

    private MaterialGramVoiceStyle() {
    }

    private static double radius(float[] shape, double theta, double rotation) {
        final double bump = Math.pow((1.0 + Math.cos(shape[0] * (theta - rotation))) / 2.0, shape[2]);
        return 1.0 - shape[1] + shape[1] * bump;
    }

    /** Draws a blob that slowly rotates and morphs from one shape to the next. Call from onDraw (UI thread). */
    public static void drawBlob(Canvas canvas, float cx, float cy, float r, Paint paint) {
        final long now = SystemClock.uptimeMillis();
        final long cycle = HOLD_MS + MORPH_MS;
        final int index = (int) ((now / cycle) % SHAPES.length);
        final int next = (index + 1) % SHAPES.length;
        final long inCycle = now % cycle;
        float t = inCycle <= HOLD_MS ? 0f : (inCycle - HOLD_MS) / (float) MORPH_MS;
        t = t * t * (3f - 2f * t);
        final double rotation = (now % 6000L) / 6000.0 * Math.PI * 2;
        final float[] a = SHAPES[index];
        final float[] b = SHAPES[next];

        BLOB.reset();
        final int steps = 120;
        for (int i = 0; i <= steps; i++) {
            final double theta = Math.PI * 2 * i / steps;
            final double ra = radius(a, theta, rotation);
            final double rb = radius(b, theta, rotation);
            final double rr = r * (ra + (rb - ra) * t);
            final float x = (float) (cx + rr * Math.cos(theta));
            final float y = (float) (cy + rr * Math.sin(theta));
            if (i == 0) {
                BLOB.moveTo(x, y);
            } else {
                BLOB.lineTo(x, y);
            }
        }
        BLOB.close();
        canvas.drawPath(BLOB, paint);
    }
}
""")

    write_text(ui_root / "MaterialGramWaveView.java", """package org.telegram.ui;

import static org.telegram.messenger.AndroidUtilities.dp;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.SystemClock;
import android.view.View;

import org.telegram.ui.ActionBar.Theme;

/** Live waveform of the voice being recorded. Fed with the amplitude (0..100) Telegram reports. */
public class MaterialGramWaveView extends View {
    public interface CancelProvider {
        float getCancelProgress();
    }

    private static final int MAX_BARS = 96;
    private static final long STEP_MS = 90;

    private final float[] levels = new float[MAX_BARS];
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF rect = new RectF();
    private CancelProvider cancelProvider;
    private long lastPush;
    private float smoothed;

    public MaterialGramWaveView(Context context) {
        super(context);
    }

    public void setCancelProvider(CancelProvider provider) {
        cancelProvider = provider;
    }

    public void reset() {
        for (int i = 0; i < levels.length; i++) {
            levels[i] = 0f;
        }
        smoothed = 0f;
        lastPush = SystemClock.uptimeMillis();
        invalidate();
    }

    /** amplitude is Telegram's 0..100 level; every call adds one bar. */
    public void pushAmplitude(float amplitude) {
        final float v = Math.max(0f, Math.min(1f, amplitude / 100f));
        smoothed += (v - smoothed) * 0.6f;
        System.arraycopy(levels, 1, levels, 0, levels.length - 1);
        levels[levels.length - 1] = smoothed;
        lastPush = SystemClock.uptimeMillis();
        invalidate();
    }

    @Override
    protected void onVisibilityChanged(View changedView, int visibility) {
        super.onVisibilityChanged(changedView, visibility);
        if (visibility == VISIBLE) {
            reset();
        }
    }

    @Override
    protected void onDraw(Canvas canvas) {
        final float w = getWidth();
        final float h = getHeight();
        final float cancel = cancelProvider == null ? 0f : Math.max(0f, Math.min(1f, cancelProvider.getCancelProgress()));
        final float left = dp(112) + (w * 0.62f - dp(112)) * cancel;
        final float right = w - dp(14);
        if (right - left < dp(24)) {
            return;
        }
        final float barWidth = dp(3);
        final float step = dp(6);
        final int count = Math.min(MAX_BARS, (int) ((right - left) / step));
        final float shift = Math.min(1f, (SystemClock.uptimeMillis() - lastPush) / (float) STEP_MS) * step;
        final int accent = Theme.getColor(Theme.key_featuredStickers_addButton);
        paint.setColor(accent);
        canvas.save();
        canvas.clipRect(left, 0, right, h);
        for (int i = 0; i < count; i++) {
            final float level = levels[levels.length - 1 - i];
            final float barHeight = dp(4) + (h - dp(4)) * (float) Math.pow(level, 0.7);
            final float x = right - barWidth - i * step - shift;
            paint.setAlpha(i < 3 ? 120 + i * 30 : 235);
            rect.set(x, (h - barHeight) / 2f, x + barWidth, (h + barHeight) / 2f);
            canvas.drawRoundRect(rect, barWidth / 2f, barWidth / 2f, paint);
        }
        canvas.restore();
        postInvalidateOnAnimation();
    }
}
""")

    # Horizontal shape picker row.
    write_text(ui_root / "MaterialGramShapePickerCell.java", """package org.telegram.ui;

import static org.telegram.messenger.AndroidUtilities.dp;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.core.graphics.ColorUtils;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.LayoutHelper;

public class MaterialGramShapePickerCell extends FrameLayout {
    public interface Listener {
        void onShapeSelected(int shape);
    }

    private static final int[] NAMES = {
        R.string.MaterialGramShapeCircle,
        R.string.MaterialGramShapeRounded,
        R.string.MaterialGramShapeSquare,
        R.string.MaterialGramShapeCookie,
        R.string.MaterialGramShapeClover,
        R.string.MaterialGramShapeBurst,
        R.string.MaterialGramShapeSun,
        R.string.MaterialGramShapePentagon,
        R.string.MaterialGramShapeHexagon,
        R.string.MaterialGramShapeHeart
    };

    private final TextView titleView;
    private final TextView subtitleView;
    private final TextView valueView;
    private final HorizontalScrollView scrollView;
    private final ShapeItemView[] items = new ShapeItemView[MaterialGramShapes.COUNT];
    private Listener listener;
    private int selected = -1;

    public MaterialGramShapePickerCell(Context context) {
        super(context);

        titleView = new TextView(context);
        titleView.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16);
        titleView.setTypeface(AndroidUtilities.bold());
        titleView.setText(LocaleController.getString(R.string.MaterialGramAvatarShapeTitle));
        addView(titleView, LayoutHelper.createFrame(LayoutHelper.WRAP_CONTENT, LayoutHelper.WRAP_CONTENT, Gravity.TOP | Gravity.LEFT, 21, 16, 130, 0));

        subtitleView = new TextView(context);
        subtitleView.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13);
        subtitleView.setText(LocaleController.getString(R.string.MaterialGramAvatarShapeInfo));
        addView(subtitleView, LayoutHelper.createFrame(LayoutHelper.WRAP_CONTENT, LayoutHelper.WRAP_CONTENT, Gravity.TOP | Gravity.LEFT, 21, 40, 130, 0));

        valueView = new TextView(context);
        valueView.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15);
        valueView.setTypeface(AndroidUtilities.bold());
        addView(valueView, LayoutHelper.createFrame(LayoutHelper.WRAP_CONTENT, LayoutHelper.WRAP_CONTENT, Gravity.TOP | Gravity.RIGHT, 0, 20, 21, 0));

        scrollView = new HorizontalScrollView(context);
        scrollView.setHorizontalScrollBarEnabled(false);
        scrollView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        final LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(dp(8), 0, dp(8), 0);
        for (int i = 0; i < MaterialGramShapes.COUNT; i++) {
            final int shape = i;
            items[i] = new ShapeItemView(context, shape, LocaleController.getString(NAMES[i]));
            items[i].setOnClickListener(v -> {
                setSelected(shape, true);
                if (listener != null) {
                    listener.onShapeSelected(shape);
                }
            });
            row.addView(items[i], new LinearLayout.LayoutParams(dp(84), dp(100)));
        }
        scrollView.addView(row, new FrameLayout.LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT));
        addView(scrollView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, 100, Gravity.TOP, 0, 76, 0, 0));

        updateColors();
    }

    public void setListener(Listener listener) {
        this.listener = listener;
    }

    public void setSelected(int shape, boolean animateScroll) {
        selected = shape;
        for (int i = 0; i < items.length; i++) {
            items[i].setPicked(i == shape);
        }
        valueView.setText(LocaleController.getString(NAMES[shape]));
        scrollView.post(() -> {
            final int target = Math.max(0, items[shape].getLeft() - dp(84));
            if (animateScroll) {
                scrollView.smoothScrollTo(target, 0);
            } else {
                scrollView.scrollTo(target, 0);
            }
        });
    }

    public void updateColors() {
        titleView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
        subtitleView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2));
        valueView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
        for (ShapeItemView item : items) {
            item.invalidate();
        }
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        super.onMeasure(widthMeasureSpec, MeasureSpec.makeMeasureSpec(dp(188), MeasureSpec.EXACTLY));
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        updateColors();
    }

    private static class ShapeItemView extends View {
        private final int shape;
        private final String label;
        private final Path path = new Path();
        private final Paint fillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint textPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();
        private boolean picked;

        ShapeItemView(Context context, int shape, String label) {
            super(context);
            this.shape = shape;
            this.label = label;
            textPaint.setTextSize(dp(12));
            textPaint.setTypeface(AndroidUtilities.bold());
            textPaint.setTextAlign(Paint.Align.CENTER);
        }

        void setPicked(boolean picked) {
            if (this.picked != picked) {
                this.picked = picked;
                invalidate();
            }
        }

        @Override
        protected void onDraw(Canvas canvas) {
            final int accent = Theme.getColor(Theme.key_featuredStickers_addButton);
            final int gray = Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2);
            final float w = getWidth();
            final float h = getHeight();
            if (picked) {
                fillPaint.setColor(ColorUtils.setAlphaComponent(accent, 46));
                rect.set(dp(4), dp(2), w - dp(4), h - dp(2));
                canvas.drawRoundRect(rect, dp(26), dp(26), fillPaint);
            }
            final float size = dp(48);
            MaterialGramShapes.fillPath(path, shape, (w - size) / 2f, dp(16), size);
            fillPaint.setColor(picked ? accent : gray);
            canvas.drawPath(path, fillPaint);
            textPaint.setColor(picked ? Theme.getColor(Theme.key_windowBackgroundWhiteBlackText) : gray);
            canvas.drawText(label, w / 2f, dp(84), textPaint);
        }
    }
}
""")

    # MaterialGram settings page. Every group is a block of rows built in updateRows().
    settings_screen = ui_root / "MaterialGramSettingsActivity.java"
    write_text(settings_screen, """package org.telegram.ui;

import android.content.Context;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import org.telegram.messenger.LocaleController;
import org.telegram.messenger.MessagesController;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.INavigationLayout;
import org.telegram.ui.Cells.HeaderCell;
import org.telegram.ui.Cells.TextCheckCell;
import org.telegram.ui.Cells.TextInfoPrivacyCell;
import org.telegram.ui.Components.LayoutHelper;
import org.telegram.ui.Components.RecyclerListView;

public class MaterialGramSettingsActivity extends BaseFragment {
    private static final int TYPE_HEADER = 0;
    private static final int TYPE_TOGGLE = 1;
    private static final int TYPE_INFO = 2;
    private static final int TYPE_SHAPES = 3;
    private static final int TYPE_COLORS = 4;

    private RecyclerListView listView;
    private ListAdapter adapter;

    // To add a setting: declare a row id here, give it a position in updateRows(),
    // then handle it in getItemViewType / onBindViewHolder / onRowClicked.
    private int rowCount;
    private int navHeaderRow;
    private int navToggleRow;
    private int navInfoRow;
    private int avatarHeaderRow;
    private int avatarShapeRow;
    private int avatarInfoRow;
    private int inputHeaderRow;
    private int inputToggleRow;
    private int voiceToggleRow;
    private int colorHeaderRow;
    private int colorPickerRow;
    private int colorInfoRow;
    private int inputInfoRow;

    private void updateRows() {
        rowCount = 0;
        navHeaderRow = rowCount++;
        navToggleRow = rowCount++;
        navInfoRow = rowCount++;
        avatarHeaderRow = rowCount++;
        avatarShapeRow = rowCount++;
        avatarInfoRow = rowCount++;
        inputHeaderRow = rowCount++;
        inputToggleRow = rowCount++;
        voiceToggleRow = rowCount++;
        inputInfoRow = rowCount++;
        colorHeaderRow = rowCount++;
        colorPickerRow = rowCount++;
        colorInfoRow = rowCount++;
    }

    @Override
    public boolean onFragmentCreate() {
        updateRows();
        return super.onFragmentCreate();
    }

    @Override
    protected boolean useSimpleActionBar() {
        return true;
    }

    @Override
    public View createView(Context context) {
        setHasOwnBackground(true);
        simpleActionBar.setBackButtonImage(R.drawable.ic_ab_back);
        simpleActionBar.setTitle(LocaleController.getString(R.string.MaterialGramSettings));
        simpleActionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                }
            }
        });

        FrameLayout frameLayout = new FrameLayout(context);
        fragmentView = frameLayout;

        listView = new RecyclerListView(context);
        listView.setSectionsDrawBackground(true);
        listView.setSections();
        listView.setLayoutManager(new LinearLayoutManager(context));
        listView.setVerticalScrollBarEnabled(false);
        listView.setAdapter(adapter = new ListAdapter(context));
        listView.setOnItemClickListener((view, position) -> onRowClicked(position));
        frameLayout.addView(listView, LayoutHelper.createFrame(
                LayoutHelper.MATCH_PARENT,
                LayoutHelper.MATCH_PARENT
        ));
        return fragmentView;
    }

    private void onRowClicked(int position) {
        if (position == navToggleRow) {
            MaterialGramSettings.setBottomNavigationEnabled(!MaterialGramSettings.isBottomNavigationEnabled());
            adapter.notifyItemChanged(navToggleRow);
            updateMainTabs();
        } else if (position == inputToggleRow) {
            MaterialGramSettings.setMaterialInputEnabled(!MaterialGramSettings.isMaterialInputEnabled());
            adapter.notifyItemChanged(inputToggleRow);
        } else if (position == voiceToggleRow) {
            MaterialGramSettings.setMaterialVoiceEnabled(!MaterialGramSettings.isMaterialVoiceEnabled());
            adapter.notifyItemChanged(voiceToggleRow);
        }
    }

    private void onColorSelected(int preset, View view) {
        MaterialGramSettings.setAppColor(preset);
        MaterialGramThemeColors.apply(preset, view);
    }

    private void onShapeSelected(int shape) {
        MaterialGramSettings.setAvatarShape(shape);
        NotificationCenter.getInstance(currentAccount).postNotificationName(
                NotificationCenter.updateInterfaces, MessagesController.UPDATE_MASK_AVATAR);
    }

    private void updateMainTabs() {
        final INavigationLayout layout = getParentLayout();
        if (layout == null) {
            return;
        }
        final MainTabsActivity mainTabs = layout.findFragment(MainTabsActivity.class);
        if (mainTabs != null) {
            mainTabs.updateMaterialGramNavigation();
        }
    }

    private class ListAdapter extends RecyclerListView.SelectionAdapter {
        private final Context context;

        private ListAdapter(Context context) {
            this.context = context;
        }

        @Override
        public int getItemCount() {
            return rowCount;
        }

        @Override
        public boolean isEnabled(RecyclerView.ViewHolder holder) {
            final int position = holder.getAdapterPosition();
            return position == navToggleRow || position == inputToggleRow || position == voiceToggleRow;
        }

        @NonNull
        @Override
        public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view;
            if (viewType == TYPE_HEADER) {
                view = new HeaderCell(context);
            } else if (viewType == TYPE_TOGGLE) {
                view = new TextCheckCell(context);
            } else if (viewType == TYPE_COLORS) {
                final MaterialGramColorPickerCell cell = new MaterialGramColorPickerCell(context);
                cell.setListener(MaterialGramSettingsActivity.this::onColorSelected);
                view = cell;
            } else if (viewType == TYPE_SHAPES) {
                final MaterialGramShapePickerCell cell = new MaterialGramShapePickerCell(context);
                cell.setListener(MaterialGramSettingsActivity.this::onShapeSelected);
                view = cell;
            } else {
                view = new TextInfoPrivacyCell(context);
            }
            view.setLayoutParams(new RecyclerView.LayoutParams(
                    RecyclerView.LayoutParams.MATCH_PARENT,
                    RecyclerView.LayoutParams.WRAP_CONTENT
            ));
            return new RecyclerListView.Holder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
            if (position == navHeaderRow) {
                ((HeaderCell) holder.itemView).setText(LocaleController.getString(R.string.MaterialGramNavigationHeader));
            } else if (position == avatarHeaderRow) {
                ((HeaderCell) holder.itemView).setText(LocaleController.getString(R.string.MaterialGramAvatarsHeader));
            } else if (position == navToggleRow) {
                ((TextCheckCell) holder.itemView).setTextAndCheck(
                        LocaleController.getString(R.string.MaterialGramNavigationEnabled),
                        MaterialGramSettings.isBottomNavigationEnabled(),
                        false
                );
            } else if (position == avatarShapeRow) {
                ((MaterialGramShapePickerCell) holder.itemView).setSelected(MaterialGramSettings.getAvatarShape(), false);
            } else if (position == navInfoRow) {
                ((TextInfoPrivacyCell) holder.itemView).setText(LocaleController.getString(R.string.MaterialGramNavigationInfo));
            } else if (position == avatarInfoRow) {
                ((TextInfoPrivacyCell) holder.itemView).setText(LocaleController.getString(R.string.MaterialGramAvatarsInfo));
            } else if (position == inputHeaderRow) {
                ((HeaderCell) holder.itemView).setText(LocaleController.getString(R.string.MaterialGramInputHeader));
            } else if (position == inputToggleRow) {
                ((TextCheckCell) holder.itemView).setTextAndCheck(
                        LocaleController.getString(R.string.MaterialGramInputButtons),
                        MaterialGramSettings.isMaterialInputEnabled(),
                        false
                );
            } else if (position == colorHeaderRow) {
                ((HeaderCell) holder.itemView).setText(LocaleController.getString(R.string.MaterialGramColorHeader));
            } else if (position == colorPickerRow) {
                ((MaterialGramColorPickerCell) holder.itemView).setSelected(MaterialGramSettings.getAppColor());
            } else if (position == colorInfoRow) {
                ((TextInfoPrivacyCell) holder.itemView).setText(LocaleController.getString(R.string.MaterialGramColorInfo));
            } else if (position == voiceToggleRow) {
                ((TextCheckCell) holder.itemView).setTextAndCheck(
                        LocaleController.getString(R.string.MaterialGramVoiceStyle),
                        MaterialGramSettings.isMaterialVoiceEnabled(),
                        false
                );
            } else if (position == inputInfoRow) {
                ((TextInfoPrivacyCell) holder.itemView).setText(LocaleController.getString(R.string.MaterialGramInputInfo));
            }
        }

        @Override
        public int getItemViewType(int position) {
            if (position == navHeaderRow || position == avatarHeaderRow || position == inputHeaderRow || position == colorHeaderRow) {
                return TYPE_HEADER;
            } else if (position == navToggleRow || position == inputToggleRow || position == voiceToggleRow) {
                return TYPE_TOGGLE;
            } else if (position == colorPickerRow) {
                return TYPE_COLORS;
            } else if (position == avatarShapeRow) {
                return TYPE_SHAPES;
            }
            return TYPE_INFO;
        }
    }

    @Override
    protected RecyclerListView getListViewForSimpleGlass() {
        return listView;
    }

    @Override
    public boolean isSupportEdgeToEdge() {
        return true;
    }
}
""")

    controller_path = ui_root / "MainTabsActivityController.java"
    write_text(controller_path, """package org.telegram.ui;

public interface MainTabsActivityController {
    void setTabsVisible(boolean visible);
    void setTabsScrollCollapsed(boolean collapsed);
    void onTabsScroll(int dy);
}
""")

    settings_path = ui_root / "SettingsActivity.java"
    settings = read_text(settings_path)
    settings = replace_once(
        settings,
        "        items.add(UItem.asCustomShadow(topView, 200 - 12));\n",
        "        items.add(UItem.asCustomShadow(topView, 200 - 12));\n"
        "        items.add(SettingCell.Factory.of(28, IconBackgroundColors.PURPLE.top, IconBackgroundColors.PURPLE.bottom, R.drawable.settings_features, getString(R.string.MaterialGramSettings), getString(R.string.MaterialGramSettingsInfo)));\n"
        "        items.add(UItem.asShadow(null));\n",
        "the top MaterialGram settings row"
    )
    settings = replace_once(
        settings,
        "            case 27: {\n                presentFragment(new HeaderSettingsActivity());\n                break;\n            }\n",
        "            case 27: {\n                presentFragment(new HeaderSettingsActivity());\n                break;\n            }\n            case 28: {\n                presentSettingFragment(new MaterialGramSettingsActivity());\n                break;\n            }\n",
        "the MaterialGram settings navigation action"
    )
    write_text(settings_path, settings)

    main_tabs_path = ui_root / "MainTabsActivity.java"
    main_tabs = read_text(main_tabs_path)
    main_tabs = replace_once(
        main_tabs,
        "    private static final int ANIMATOR_ID_TABS_VISIBLE = 0;\n"
        "    private final BoolAnimator animatorTabsVisible = new BoolAnimator(ANIMATOR_ID_TABS_VISIBLE,\n"
        "        this, CubicBezierInterpolator.EASE_OUT_QUINT, 380, true);\n",
        "    private static final int ANIMATOR_ID_TABS_VISIBLE = 0;\n"
        "    private static final int ANIMATOR_ID_TABS_SCROLL_COLLAPSED = 1;\n"
        "    private final BoolAnimator animatorTabsVisible = new BoolAnimator(ANIMATOR_ID_TABS_VISIBLE,\n"
        "        this, CubicBezierInterpolator.EASE_OUT_QUINT, 380, true);\n"
        "    private final BoolAnimator animatorTabsScrollCollapsed = new BoolAnimator(ANIMATOR_ID_TABS_SCROLL_COLLAPSED,\n"
        "        this, CubicBezierInterpolator.EASE_OUT_QUINT, 240, false);\n",
        "the separate scroll-collapse animator"
    )
    main_tabs = replace_once(
        main_tabs,
        "        if (id == ANIMATOR_ID_TABS_VISIBLE) {\n"
        "            checkUi_tabsPosition();\n"
        "            checkUi_fadeView();\n"
        "        }\n",
        "        if (id == ANIMATOR_ID_TABS_VISIBLE || id == ANIMATOR_ID_TABS_SCROLL_COLLAPSED) {\n"
        "            checkUi_tabsPosition();\n"
        "            checkUi_fadeView();\n"
        "        }\n",
        "the scroll-collapse animation callback"
    )
    main_tabs = replace_once(
        main_tabs,
        "import android.widget.FrameLayout;\n",
        "import android.widget.FrameLayout;\nimport android.widget.ImageView;\n",
        "the MainTabsActivity ImageView import"
    )
    main_tabs = replace_once(
        main_tabs,
        "    private View fadeView;\n",
        "    private View fadeView;\n"
        "    private View materialGramSearchButton;\n",
        "the MaterialGram search button field"
    )
    # Selecting a tab always re-expands the capsule.
    main_tabs = replace_once(
        main_tabs,
        "    public void selectTab(int position, boolean animated) {\n"
        "        for (int a = 0; a < tabs.length; a++) {\n",
        "    public void selectTab(int position, boolean animated) {\n"
        "        animatorTabsScrollCollapsed.setValue(false, animated);\n"
        "        applyMaterialGramCollapse(false, animated);\n"
        "        for (int a = 0; a < tabs.length; a++) {\n",
        "the tab selection recovery"
    )
    main_tabs = replace_once(
        main_tabs,
        "        showAccountChangeHint();\n",
        "        showAccountChangeHint();\n"
        "        updateMaterialGramNavigation();\n",
        "the MainTabsActivity resume refresh"
    )
    main_tabs = replace_once(
        main_tabs,
        "        tabsViewBackground.setRadius(dp(DialogsActivity.MAIN_TABS_HEIGHT / 2f));\n"
        "        tabsViewBackground.setPadding(dp(DialogsActivity.MAIN_TABS_MARGIN - 0.334f));\n"
        "        tabsView.setBackground(tabsViewBackground);\n",
        "        tabsViewBackground.setRadius(dp(DialogsActivity.MAIN_TABS_HEIGHT / 2f));\n"
        "        tabsViewBackground.setPadding(dp(DialogsActivity.MAIN_TABS_MARGIN - 0.334f));\n"
        "        tabsView.setBackground(tabsViewBackground);\n"
        "\n"
        "        FrameLayout searchButton = new FrameLayout(context);\n"
        "        materialGramSearchButton = searchButton;\n"
        "        searchButton.setContentDescription(getString(R.string.Search));\n"
        "        ImageView searchIcon = new ImageView(context);\n"
        "        searchIcon.setImageResource(R.drawable.outline_header_search);\n"
        "        searchIcon.setColorFilter(getThemedColor(Theme.key_glass_tabUnselected));\n"
        "        searchButton.addView(searchIcon, LayoutHelper.createFrame(24, 24, Gravity.CENTER));\n"
        "        BlurredBackgroundDrawable searchButtonBackground = iBlur3FactoryGlass.create(searchButton, BlurredBackgroundProviderImpl.mainTabs(resourceProvider));\n"
        "        searchButtonBackground.setRadius(dp(22));\n"
        "        searchButton.setBackground(searchButtonBackground);\n"
        "        searchButton.setOnClickListener(v -> {\n"
        "            if (dialogsActivity == null) {\n"
        "                prepareDialogsActivity(null);\n"
        "            }\n"
        "            selectTab(POSITION_CHATS, true);\n"
        "            viewPager.scrollToPosition(POSITION_CHATS);\n"
        "            if (dialogsActivity != null) {\n"
        "                dialogsActivity.search(\"\", true);\n"
        "            }\n"
        "        });\n",
        "the MaterialGram search button construction"
    )
    main_tabs = replace_once(
        main_tabs,
        "        tabsViewWrapper.addView(tabsView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, DialogsActivity.MAIN_TABS_HEIGHT_WITH_MARGINS, Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL));\n"
        "        tabsViewWrapper.setClipToPadding(false);\n"
        "        contentView.addView(tabsViewWrapper, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.BOTTOM));\n",
        "        tabsViewWrapper.addView(tabsView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, DialogsActivity.MAIN_TABS_HEIGHT_WITH_MARGINS, Gravity.BOTTOM | Gravity.LEFT, 8, 0, 60, 0));\n"
        "        tabsViewWrapper.addView(searchButton, LayoutHelper.createFrame(44, 44, Gravity.RIGHT | Gravity.CENTER_VERTICAL, 0, 0, 8, 0));\n"
        "        tabsViewWrapper.setClipToPadding(false);\n"
        "        contentView.addView(tabsViewWrapper, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.BOTTOM));\n",
        "the MainTabsActivity capsule and search-button layout"
    )
    # The refresh + collapse helpers. The native capsule is never hidden here.
    main_tabs = replace_once(
        main_tabs,
        "    private class MainTabsActivityControllerImpl implements MainTabsActivityController {\n",
        "    /** Collapsed: only the selected tab stays in the capsule (expanded with its label). */\n"
        "    private void applyMaterialGramCollapse(boolean collapsed, boolean animated) {\n"
        "        if (tabsView == null || tabs == null || viewPager == null) {\n"
        "            return;\n"
        "        }\n"
        "        final boolean showCalls = getUserConfig().showCallsTab;\n"
        "        final int selected = viewPager.getCurrentPosition();\n"
        "        for (int i = 0; i < tabs.length; i++) {\n"
        "            if (tabs[i] == null) {\n"
        "                continue;\n"
        "            }\n"
        "            final boolean exists = i == INDEX_SETTINGS ? !showCalls : (i == INDEX_CALLS ? showCalls : true);\n"
        "            final boolean isSelected = indexToPosition(i) == selected;\n"
        "            tabsView.setViewVisible(tabs[i], exists && (!collapsed || isSelected), animated);\n"
        "        }\n"
        "    }\n"
        "\n"
        "    public void updateMaterialGramNavigation() {\n"
        "        final boolean enabled = MaterialGramSettings.isBottomNavigationEnabled();\n"
        "        final Runnable refresh = () -> {\n"
        "            if (tabsView == null || tabsViewWrapper == null) {\n"
        "                return;\n"
        "            }\n"
        "            animatorTabsScrollCollapsed.setValue(false, false);\n"
        "            applyMaterialGramCollapse(false, false);\n"
        "            if (materialGramSearchButton != null) {\n"
        "                materialGramSearchButton.setVisibility(enabled ? View.VISIBLE : View.GONE);\n"
        "            }\n"
        "            final ViewGroup.LayoutParams rawLp = tabsView.getLayoutParams();\n"
        "            if (rawLp instanceof FrameLayout.LayoutParams) {\n"
        "                final FrameLayout.LayoutParams lp = (FrameLayout.LayoutParams) rawLp;\n"
        "                lp.gravity = Gravity.BOTTOM | (enabled ? Gravity.LEFT : Gravity.CENTER_HORIZONTAL);\n"
        "                lp.leftMargin = enabled ? dp(8) : 0;\n"
        "                lp.rightMargin = enabled ? dp(60) : 0;\n"
        "                tabsView.setLayoutParams(lp);\n"
        "            }\n"
        "            if (dialogsActivity != null) {\n"
        "                dialogsActivity.resetMaterialGramTabsScrollVisibility();\n"
        "            }\n"
        "            checkUi_tabsPosition();\n"
        "            checkUi_fadeView();\n"
        "            tabsViewWrapper.requestLayout();\n"
        "        };\n"
        "        if (tabsViewWrapper != null && tabsViewWrapper.isAttachedToWindow()) {\n"
        "            tabsViewWrapper.post(refresh);\n"
        "        } else {\n"
        "            refresh.run();\n"
        "        }\n"
        "    }\n"
        "\n"
        "    private class MainTabsActivityControllerImpl implements MainTabsActivityController {\n",
        "the MaterialGram navigation refresh method"
    )
    main_tabs = replace_once(
        main_tabs,
        "    private class MainTabsActivityControllerImpl implements MainTabsActivityController {\n"
        "        @Override\n"
        "        public void setTabsVisible(boolean visible) {\n"
        "            animatorTabsVisible.setValue(visible, true);\n"
        "        }\n"
        "    }\n",
        "    private class MainTabsActivityControllerImpl implements MainTabsActivityController {\n"
        "        @Override\n"
        "        public void setTabsVisible(boolean visible) {\n"
        "            animatorTabsVisible.setValue(visible, true);\n"
        "        }\n"
        "\n"
        "        @Override\n"
        "        public void setTabsScrollCollapsed(boolean collapsed) {\n"
        "            if (MaterialGramSettings.isBottomNavigationEnabled()) {\n"
        "                animatorTabsScrollCollapsed.setValue(collapsed, true);\n"
        "                applyMaterialGramCollapse(collapsed, true);\n"
        "            }\n"
        "        }\n"
        "    }\n",
        "the independent scroll-collapse controller method"
    )
    main_tabs = replace_once(
        main_tabs,
        "        updateLayout();\n        checkUnreadCount(false);\n        return contentView;\n",
        "        updateLayout();\n        updateMaterialGramNavigation();\n        checkUnreadCount(false);\n        return contentView;\n",
        "initial MaterialGram navigation synchronization"
    )

    # ---- Capsule width animation + scroll collapse on every tab -------------
    main_tabs = replace_once(
        main_tabs,
        '''    private View materialGramSearchButton;
''',
        '''    private View materialGramSearchButton;
    private android.animation.ValueAnimator materialGramWidthAnimator;
    private boolean materialGramCollapsedState;
    private boolean materialGramLayoutCollapsed;
    private float materialGramScrollAccum;
    private long materialGramLastToggle;
    private Runnable materialGramPendingStep;
    private final java.util.Set<BaseFragment> materialGramScrollHooked =
        java.util.Collections.newSetFromMap(new java.util.WeakHashMap<BaseFragment, Boolean>());
''',
        "the MaterialGram width animator fields"
    )
    main_tabs = replace_once(
        main_tabs,
        '''            tabsView.setViewVisible(tabs[i], exists && (!collapsed || isSelected), animated);
        }
    }
''',
        '''            tabsView.setViewVisible(tabs[i], exists && (!collapsed || isSelected), animated);
        }
        animateMaterialGramCapsuleWidth(collapsed, animated);
    }

    /** Collapsed capsule hugs the selected tab; expanded goes back to the full native width. */
    private void animateMaterialGramCapsuleWidth(boolean collapsed, boolean animated) {
        if (tabsView == null || tabsViewWrapper == null) {
            return;
        }
        final ViewGroup.LayoutParams raw = tabsView.getLayoutParams();
        if (!(raw instanceof FrameLayout.LayoutParams)) {
            return;
        }
        final FrameLayout.LayoutParams lp = (FrameLayout.LayoutParams) raw;
        final int available = tabsViewWrapper.getWidth() - tabsViewWrapper.getPaddingLeft()
            - tabsViewWrapper.getPaddingRight() - lp.leftMargin - lp.rightMargin;
        if (available <= 0) {
            return;
        }
        final int expandedWidth = Math.min(available, dp(328 + DialogsActivity.MAIN_TABS_MARGIN * 2));
        final int target = collapsed ? Math.min(expandedWidth, dp(116)) : expandedWidth;
        if (!collapsed && lp.width == ViewGroup.LayoutParams.MATCH_PARENT) {
            return;
        }
        if (collapsed && lp.width == target) {
            return;
        }
        if (materialGramWidthAnimator != null) {
            materialGramWidthAnimator.cancel();
            materialGramWidthAnimator = null;
        }
        if (!animated) {
            lp.width = collapsed ? target : ViewGroup.LayoutParams.MATCH_PARENT;
            tabsView.setLayoutParams(lp);
            return;
        }
        final int from = lp.width > 0 ? lp.width : (tabsView.getWidth() > 0 ? tabsView.getWidth() : expandedWidth);
        final android.animation.ValueAnimator animator = android.animation.ValueAnimator.ofInt(from, target);
        animator.setDuration(240);
        animator.setInterpolator(CubicBezierInterpolator.EASE_OUT_QUINT);
        animator.addUpdateListener(a -> {
            lp.width = (int) a.getAnimatedValue();
            tabsView.setLayoutParams(lp);
        });
        animator.addListener(new android.animation.AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator animation) {
                if (!collapsed) {
                    lp.width = ViewGroup.LayoutParams.MATCH_PARENT;
                    tabsView.setLayoutParams(lp);
                }
                if (materialGramWidthAnimator == animator) {
                    materialGramWidthAnimator = null;
                }
            }
        });
        materialGramWidthAnimator = animator;
        animator.start();
    }

    /** Scroll filter: needs a real swipe in one direction, and never flips faster than every 350 ms. */
    private void materialGramOnScroll(int dy) {
        if (dy == 0 || !MaterialGramSettings.isBottomNavigationEnabled()) {
            return;
        }
        if ((dy > 0) != (materialGramScrollAccum > 0)) {
            materialGramScrollAccum = 0;
        }
        materialGramScrollAccum += dy;
        final boolean wantCollapsed = materialGramScrollAccum > 0;
        final float needed = wantCollapsed ? dp(36) : dp(20);
        if (Math.abs(materialGramScrollAccum) < needed || wantCollapsed == materialGramCollapsedState) {
            return;
        }
        final long now = android.os.SystemClock.uptimeMillis();
        if (now - materialGramLastToggle < 350) {
            return;
        }
        materialGramLastToggle = now;
        materialGramScrollAccum = 0;
        materialGramSetCollapsed(wantCollapsed);
    }

    private void materialGramSetCollapsed(boolean collapsed) {
        if (!MaterialGramSettings.isBottomNavigationEnabled()) {
            return;
        }
        materialGramCollapsedState = collapsed;
        animatorTabsScrollCollapsed.setValue(collapsed, true);
        applyMaterialGramCollapse(collapsed, true);
    }

    private androidx.recyclerview.widget.RecyclerView materialGramFindList(View view) {
        if (view instanceof androidx.recyclerview.widget.RecyclerView) {
            return (androidx.recyclerview.widget.RecyclerView) view;
        }
        if (view instanceof ViewGroup) {
            final ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) {
                final androidx.recyclerview.widget.RecyclerView found = materialGramFindList(group.getChildAt(i));
                if (found != null) {
                    return found;
                }
            }
        }
        return null;
    }

    /** Contacts, Settings and Profile pages: collapse the capsule while their list scrolls down. */
    private void hookMaterialGramScroll() {
        for (int a = 0, N = fragmentsArr.size(); a < N; a++) {
            final BaseFragment fragment = fragmentsArr.valueAt(a).fragment;
            if (fragment == null || fragment instanceof DialogsActivity || fragment.fragmentView == null) {
                continue;
            }
            if (materialGramScrollHooked.contains(fragment)) {
                continue;
            }
            final androidx.recyclerview.widget.RecyclerView list = materialGramFindList(fragment.fragmentView);
            if (list == null) {
                continue;
            }
            materialGramScrollHooked.add(fragment);
            list.addOnScrollListener(new androidx.recyclerview.widget.RecyclerView.OnScrollListener() {
                @Override
                public void onScrolled(@NonNull androidx.recyclerview.widget.RecyclerView rv, int dx, int dy) {
                    if (!MaterialGramSettings.isBottomNavigationEnabled() || getCurrentVisibleFragment() != fragment) {
                        return;
                    }
                    if (!rv.canScrollVertically(-1)) {
                        materialGramSetCollapsed(false);
                    } else {
                        materialGramOnScroll(dy);
                    }
                }
            });
        }
    }
''',
        "the MaterialGram capsule width and scroll hook methods"
    )
    main_tabs = replace_once(
        main_tabs,
        '''                animatorTabsScrollCollapsed.setValue(collapsed, true);
                applyMaterialGramCollapse(collapsed, true);
            }
        }
    }
''',
        '''                materialGramSetCollapsed(collapsed);
            }
        }

        @Override
        public void onTabsScroll(int dy) {
            materialGramOnScroll(dy);
        }
    }
''',
        "the controller collapse delegation"
    )
    main_tabs = replace_once(
        main_tabs,
        '''                blur3_updateFragmentsGlass();
            }

            @Override
            protected void dispatchDraw''',
        '''                blur3_updateFragmentsGlass();
                hookMaterialGramScroll();
            }

            @Override
            protected void dispatchDraw''',
        "the MaterialGram scroll hook trigger"
    )

    # ---- Sequence tabs and capsule width so labels are never squeezed ------
    main_tabs = replace_once(
        main_tabs,
        '''    private void applyMaterialGramCollapse(boolean collapsed, boolean animated) {
        if (tabsView == null || tabs == null || viewPager == null) {
            return;
        }
''',
        '''    private void applyMaterialGramCollapse(boolean collapsed, boolean animated) {
        if (tabsView == null || tabs == null || viewPager == null) {
            return;
        }
        if (materialGramPendingStep != null) {
            tabsView.removeCallbacks(materialGramPendingStep);
            materialGramPendingStep = null;
        }
        if (!animated || (!collapsed && !materialGramLayoutCollapsed)) {
            materialGramLayoutCollapsed = collapsed;
            applyMaterialGramTabs(collapsed, animated);
            animateMaterialGramCapsuleWidth(collapsed, animated);
            return;
        }
        materialGramLayoutCollapsed = collapsed;
        if (collapsed) {
            // other tabs leave first, then the capsule shrinks around the selected one
            applyMaterialGramTabs(true, true);
            materialGramPendingStep = () -> {
                materialGramPendingStep = null;
                animateMaterialGramCapsuleWidth(true, true);
            };
        } else {
            // the capsule widens first, then the other tabs come back
            animateMaterialGramCapsuleWidth(false, true);
            materialGramPendingStep = () -> {
                materialGramPendingStep = null;
                applyMaterialGramTabs(false, true);
            };
        }
        tabsView.postDelayed(materialGramPendingStep, 140);
    }

    private void applyMaterialGramTabs(boolean collapsed, boolean animated) {
        if (tabsView == null || tabs == null || viewPager == null) {
            return;
        }
''',
        "the sequenced MaterialGram collapse"
    )
    main_tabs = replace_once(
        main_tabs,
        '''            tabsView.setViewVisible(tabs[i], exists && (!collapsed || isSelected), animated);
        }
        animateMaterialGramCapsuleWidth(collapsed, animated);
    }
''',
        '''            tabsView.setViewVisible(tabs[i], exists && (!collapsed || isSelected), animated);
        }
    }
''',
        "the tab visibility without width side effect"
    )
    write_text(main_tabs_path, main_tabs)

    dialogs_path = ui_root / "DialogsActivity.java"
    dialogs = read_text(dialogs_path)
    dialogs = replace_once(
        dialogs,
        "    public void onBecomeFullyVisible() {\n"
        "        super.onBecomeFullyVisible();\n",
        "    public void onBecomeFullyVisible() {\n"
        "        super.onBecomeFullyVisible();\n"
        "        if (mainTabsActivityController != null) {\n"
        "            mainTabsActivityController.setTabsScrollCollapsed(false);\n"
        "            checkUi_mainTabsVisible();\n"
        "        }\n",
        "the chat screen navigation restore"
    )
    dialogs = replace_once(
        dialogs,
        "    public void setMainTabsActivityController(MainTabsActivityController controller) {\n"
        "        mainTabsActivityController = controller;\n"
        "    }\n",
        "    public void setMainTabsActivityController(MainTabsActivityController controller) {\n"
        "        mainTabsActivityController = controller;\n"
        "    }\n"
        "\n"
        "    public void resetMaterialGramTabsScrollVisibility() {\n"
        "        if (mainTabsActivityController != null) {\n"
        "            mainTabsActivityController.setTabsScrollCollapsed(false);\n"
        "        }\n"
        "        checkUi_mainTabsVisible();\n"
        "    }\n",
        "the chat-list navigation visibility reset"
    )
    dialogs = replace_once(
        dialogs,
        "                    viewPage.dialogsItemAnimator.onListScroll(-dy);\n",
        "                    viewPage.dialogsItemAnimator.onListScroll(-dy);\n"
        "                    if (dy != 0 && mainTabsActivityController != null && viewPages != null && viewPages.length > 0 && recyclerView == viewPages[0].listView && (viewPage.dialogsType == DIALOGS_TYPE_DEFAULT || viewPage.dialogsType == 7 || viewPage.dialogsType == 8) && !searching) {\n"
        "                        mainTabsActivityController.onTabsScroll(dy);\n"
        "                    }\n",
        "the chat-list scroll direction handler"
    )
    write_text(dialogs_path, dialogs)

    strings_path = UPSTREAM / "TMessagesProj" / "src" / "main" / "res" / "values" / "strings.xml"
    strings = read_text(strings_path)
    additions = [
        ('MaterialGramSettings', 'Настройки MaterialGram'),
        ('MaterialGramSettingsInfo', 'Дополнительные настройки интерфейса MaterialGram'),
        ('MaterialGramNavigationHeader', 'Нижняя панель навигации'),
        ('MaterialGramNavigationEnabled', 'Включить панель MaterialGram'),
        ('MaterialGramNavigationInfo', 'Капсула с кнопкой поиска. При прокрутке чатов вниз она сворачивается до одной вкладки, при прокрутке вверх раскрывается. Если выключить, остаётся обычная панель Telegram.'),
        ('MaterialGramAvatarsHeader', 'Аватарки и иконки'),
        ('MaterialGramAvatarShapeTitle', 'Аватарки чатов'),
        ('MaterialGramAvatarShapeInfo', 'форма аватарок, видно только у тебя'),
        ('MaterialGramAvatarsInfo', 'Форма применяется только на этом устройстве и не видна другим людям.'),
        ('MaterialGramInputHeader', 'Панель ввода'),
        ('MaterialGramInputButtons', 'Панель ввода Material You'),
        ('MaterialGramColorHeader', 'Цвет приложения'),
        ('MaterialGramColorBlue', 'Синий'),
        ('MaterialGramColorGreen', 'Зелёный'),
        ('MaterialGramColorPink', 'Розовый'),
        ('MaterialGramColorInfo', 'Цвет применяется к светлой и тёмной теме сразу. Если у тебя своя тема, цвет может не поменяться.'),
        ('MaterialGramVoiceStyle', 'Голосовое Material You'),
        ('MaterialGramInputInfo', 'Панель: поле ввода, скрепка и микрофон становятся отдельными элементами (только в обычных чатах). Голосовое: вместо красной точки меняющаяся фигура, рядом живая волна звука; подсказка «влево для отмены» скрывается, жест остаётся.'),
        ('MaterialGramShapeCircle', 'Круг'),
        ('MaterialGramShapeRounded', 'Скруглённый'),
        ('MaterialGramShapeSquare', 'Квадрат'),
        ('MaterialGramShapeCookie', 'Печенье'),
        ('MaterialGramShapeClover', 'Клевер'),
        ('MaterialGramShapeBurst', 'Вспышка'),
        ('MaterialGramShapeSun', 'Солнце'),
        ('MaterialGramShapePentagon', 'Пятиугольник'),
        ('MaterialGramShapeHexagon', 'Шестиугольник'),
        ('MaterialGramShapeHeart', 'Сердце'),
    ]
    for name, value in additions:
        if f'name="{name}"' not in strings:
            entry = f'    <string name="{name}">{value}</string>\n'
            strings = replace_once(strings, "</resources>", entry + "</resources>", f"the {name} string resource")
    write_text(strings_path, strings)

    print("MaterialGram adaptive navigation and its settings screen were applied.")


def patch_materialgram_avatars() -> None:
    """Make every circular avatar follow the shape chosen in MaterialGram settings."""
    java_root = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram"

    # Photo avatars: ImageReceiver draws them through a bitmap shader at two places.
    receiver_path = java_root / "messenger" / "ImageReceiver.java"
    receiver = read_text(receiver_path)
    old_round = "                                        canvas.drawRoundRect(roundRect, roundRadius[0], roundRadius[0], roundPaint);\n"
    count = receiver.count(old_round)
    if count != 2:
        fail(f"Could not safely patch ImageReceiver avatar drawing: expected two matches, found {count}.")
    receiver = receiver.replace(
        old_round,
        "                                        if (!org.telegram.ui.MaterialGramShapes.drawAvatarRoundRect(canvas, roundRect, roundRadius[0], roundPaint)) {\n"
        "                                            canvas.drawRoundRect(roundRect, roundRadius[0], roundRadius[0], roundPaint);\n"
        "                                        }\n"
    )
    write_text(receiver_path, receiver)

    # Letter / colour avatars without a photo.
    drawable_path = java_root / "ui" / "Components" / "AvatarDrawable.java"
    drawable = read_text(drawable_path)
    drawable = replace_once(
        drawable,
        "                canvas.drawCircle(size / 2.0f, size / 2.0f, size / 2.0f, backgroundPaint);\n",
        "                if (!org.telegram.ui.MaterialGramShapes.drawAvatarCircle(canvas, size, backgroundPaint)) {\n"
        "                    canvas.drawCircle(size / 2.0f, size / 2.0f, size / 2.0f, backgroundPaint);\n"
        "                }\n",
        "the AvatarDrawable circle background"
    )
    # ImageReceiver hands avatars a round radius, so the usual path is this one.
    # The pinned upstream formats this line slightly differently from other versions, so match it loosely.
    pattern = re.compile(r"canvas\.drawRoundRect\(\s*([^,;()]+?)\s*,\s*roundRadius\s*,\s*roundRadius\s*,\s*backgroundPaint\s*\)\s*;")
    def wrap_round(match):
        rect = match.group(1)
        return (
            "if (!org.telegram.ui.MaterialGramShapes.drawAvatarRoundRect(canvas, " + rect + ", roundRadius, backgroundPaint)) {\n"
            "                    canvas.drawRoundRect(" + rect + ", roundRadius, roundRadius, backgroundPaint);\n"
            "                }"
        )
    drawable, wrapped = pattern.subn(wrap_round, drawable)
    if wrapped == 0:
        print("WARNING: no rounded avatar background found in AvatarDrawable; letter avatars may keep a round shape.")
        for number, line in enumerate(drawable.splitlines(), 1):
            if "drawRoundRect" in line or "roundRadius" in line or "drawCircle" in line:
                print(f"  AvatarDrawable:{number}: {line.strip()}")
    else:
        print(f"MaterialGram: wrapped {wrapped} rounded AvatarDrawable background(s).")
    write_text(drawable_path, drawable)

    print("MaterialGram avatar shapes were applied.")


def patch_materialgram_input() -> None:
    """Material You shaped mic/send buttons in the chat input panel (optional, off by default)."""
    enter_path = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Components" / "ChatActivityEnterView.java"
    enter = read_text(enter_path)
    enter = replace_once(
        enter,
        "canvas.drawRoundRect(backgroundRect, r, r, paint);",
        "if (!org.telegram.ui.MaterialGramInputStyle.drawActionButton(canvas, backgroundRect, paint)) {\n"
        "                        canvas.drawRoundRect(backgroundRect, r, r, paint);\n"
        "                    }",
        "the mic button background in ChatActivityEnterView"
    )
    enter = replace_once(
        enter,
        "canvas.drawRoundRect(backgroundRect, dp(RADIUS), dp(RADIUS), backgroundPaint);",
        "if (!org.telegram.ui.MaterialGramInputStyle.drawActionButton(canvas, backgroundRect, backgroundPaint)) {\n"
        "                    canvas.drawRoundRect(backgroundRect, dp(RADIUS), dp(RADIUS), backgroundPaint);\n"
        "                }",
        "the send button background in ChatActivityEnterView"
    )
    write_text(enter_path, enter)
    print("MaterialGram input panel style was applied.")


def patch_materialgram_split_input() -> None:
    """Split the one glass island of the chat input into field | attach | mic (plain chats only)."""
    java_root = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui"

    # 1) The enter view tells the container when a split is allowed and how visible the attach button is.
    enter_path = java_root / "Components" / "ChatActivityEnterView.java"
    enter = read_text(enter_path)
    enter = replace_once(
        enter,
        "    public ImageView getAttachButton() {\n",
        "    /** MaterialGram: attach button visibility 0..1 when the island may be split; -1 when it must stay whole. */\n"
        "    public float materialGramAttachProgress() {\n"
        "        if (attachButton == null || attachButton.getVisibility() != View.VISIBLE) {\n"
        "            return -1f;\n"
        "        }\n"
        "        if (recordInterfaceState != 0 || editingMessageObject != null || !isChat) {\n"
        "            return -1f;\n"
        "        }\n"
        "        final View[] others = new View[]{botButton, notifyButton, scheduledButton, giftButton, suggestButton, senderSelectView, botCommandsMenuButton, doneButton};\n"
        "        for (View other : others) {\n"
        "            if (other != null && other.getVisibility() == View.VISIBLE) {\n"
        "                return -1f;\n"
        "            }\n"
        "        }\n"
        "        return Math.max(0f, Math.min(1f, attachButton.getAlpha()));\n"
        "    }\n"
        "\n"
        "    public ImageView getAttachButton() {\n",
        "the MaterialGram attach progress method"
    )
    write_text(enter_path, enter)

    # 2) The container draws two glass pieces instead of one.
    container_path = java_root / "Components" / "chat" / "ChatInputViewsContainer.java"
    container = read_text(container_path)
    container = replace_once(
        container,
        "import org.telegram.ui.Components.inset.WindowInsetsProvider;\n",
        "import org.telegram.ui.Components.inset.WindowInsetsProvider;\n"
        "import org.telegram.ui.MaterialGramSettings;\n",
        "the container MaterialGramSettings import"
    )
    container = replace_once(
        container,
        "    public void setUnderKeyboardBackgroundDrawable(BlurredBackgroundDrawable drawable) {\n",
        "    public interface SplitProvider {\n"
        "        float getAttachProgress();\n"
        "    }\n"
        "\n"
        "    private SplitProvider splitProvider;\n"
        "    private BlurredBackgroundDrawable splitAttachDrawable;\n"
        "    private boolean splitApplied;\n"
        "    private int inputBubbleAlpha = 255;\n"
        "    private final Rect tmpRect2 = new Rect();\n"
        "\n"
        "    public void setMaterialGramSplitProvider(SplitProvider provider) {\n"
        "        splitProvider = provider;\n"
        "        invalidate();\n"
        "    }\n"
        "\n"
        "    public void setSplitAttachDrawable(BlurredBackgroundDrawable drawable) {\n"
        "        splitAttachDrawable = drawable;\n"
        "        splitAttachDrawable.setPadding(dp(7));\n"
        "        splitAttachDrawable.setRadius(dp(16), dp(8), dp(8), dp(22));\n"
        "    }\n"
        "\n"
        "    private float materialGramSplitProgress() {\n"
        "        if (splitProvider == null || !MaterialGramSettings.isMaterialInputEnabled()) {\n"
        "            return -1f;\n"
        "        }\n"
        "        if (inputBubbleOffsetLeft != 0f || inputBubbleOffsetRight != 0f) {\n"
        "            return -1f;\n"
        "        }\n"
        "        return splitProvider.getAttachProgress();\n"
        "    }\n"
        "\n"
        "    public void setUnderKeyboardBackgroundDrawable(BlurredBackgroundDrawable drawable) {\n",
        "the container split fields"
    )
    container = replace_once(
        container,
        "        if (underKeyboardBackgroundDrawable != null) {\n"
        "            underKeyboardBackgroundDrawable.updateColors();\n"
        "        }\n"
        "        invalidate();\n",
        "        if (underKeyboardBackgroundDrawable != null) {\n"
        "            underKeyboardBackgroundDrawable.updateColors();\n"
        "        }\n"
        "        if (splitAttachDrawable != null) {\n"
        "            splitAttachDrawable.updateColors();\n"
        "        }\n"
        "        invalidate();\n",
        "the container split colors"
    )
    container = replace_once(
        container,
        "        if (blurredBackgroundDrawable != null) {\n"
        "            blurredBackgroundDrawable.setAlpha(alpha);\n"
        "        }\n",
        "        inputBubbleAlpha = alpha;\n"
        "        if (blurredBackgroundDrawable != null) {\n"
        "            blurredBackgroundDrawable.setAlpha(alpha);\n"
        "        }\n",
        "the container bubble alpha"
    )
    container = replace_once(
        container,
        "        blurredBackgroundDrawable.setBounds(tmpRect);\n"
        "        if (drawInputBackground)\n"
        "            blurredBackgroundDrawable.draw(canvas);\n",
        "        final float splitProgress = materialGramSplitProgress();\n"
        "        final boolean split = splitProgress >= 0f;\n"
        "        if (split != splitApplied) {\n"
        "            splitApplied = split;\n"
        "            blurredBackgroundDrawable.setRadius(dp(split ? 16 : INPUT_BUBBLE_RADIUS));\n"
        "        }\n"
        "        if (split) {\n"
        "            final int visibleBottom = tmpRect.bottom - dp(7);\n"
        "            final int visibleRight = tmpRect.right - dp(7);\n"
        "            if (splitAttachDrawable != null && splitProgress > 0.01f) {\n"
        "                tmpRect2.set(\n"
        "                    visibleRight - dp(86) - dp(7),\n"
        "                    visibleBottom - dp(42) - dp(7),\n"
        "                    visibleRight - dp(46) + dp(7),\n"
        "                    visibleBottom - dp(2) + dp(7)\n"
        "                );\n"
        "                splitAttachDrawable.setBounds(tmpRect2);\n"
        "                splitAttachDrawable.setAlpha(Math.round(inputBubbleAlpha * splitProgress));\n"
        "                if (drawInputBackground) {\n"
        "                    splitAttachDrawable.draw(canvas);\n"
        "                }\n"
        "            }\n"
        "            tmpRect.right -= Math.round(dp(46) + dp(44) * splitProgress);\n"
        "        }\n"
        "\n"
        "        blurredBackgroundDrawable.setBounds(tmpRect);\n"
        "        if (drawInputBackground)\n"
        "            blurredBackgroundDrawable.draw(canvas);\n",
        "the container split drawing"
    )
    write_text(container_path, container)

    # 3) ChatActivity creates the second glass piece and connects the enter view.
    chat_path = java_root / "ChatActivity.java"
    chat = read_text(chat_path)
    chat = replace_once(
        chat,
        "        chatInputViewsContainer.setUnderKeyboardBackgroundDrawable(\n"
        "            glassBackgroundDrawableFactoryFrosted.create(chatInputViewsContainer, blurredBackgroundColorProvider));\n",
        "        chatInputViewsContainer.setUnderKeyboardBackgroundDrawable(\n"
        "            glassBackgroundDrawableFactoryFrosted.create(chatInputViewsContainer, blurredBackgroundColorProvider));\n"
        "        chatInputViewsContainer.setSplitAttachDrawable(\n"
        "            glassBackgroundDrawableFactory.create(chatInputViewsContainer, blurredBackgroundColorProvider));\n",
        "the ChatActivity split attach glass"
    )
    chat = replace_once(
        chat,
        "        chatInputBubbleContainer.addView(chatActivityEnterView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.LEFT | Gravity.BOTTOM, 7, 0, 7, 0));\n",
        "        chatInputBubbleContainer.addView(chatActivityEnterView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.LEFT | Gravity.BOTTOM, 7, 0, 7, 0));\n"
        "        chatInputViewsContainer.setMaterialGramSplitProvider(chatActivityEnterView::materialGramAttachProgress);\n",
        "the ChatActivity split provider"
    )
    write_text(chat_path, chat)
    print("MaterialGram split input panel was applied.")


def patch_materialgram_voice() -> None:
    """Material You look for the voice recording panel (optional, off by default)."""
    enter_path = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Components" / "ChatActivityEnterView.java"
    enter = read_text(enter_path)

    # 1) A morphing blob instead of the blinking red dot.
    enter = replace_once(
        enter,
        "        protected void onDraw(Canvas canvas) {\n"
        "            if (playing) {\n"
        "                drawable.setAlpha((int) (255 * alpha));\n"
        "            }\n"
        "            redDotPaint.setAlpha((int) (255 * alpha));\n",
        "        protected void onDraw(Canvas canvas) {\n"
        "            if (!playing && org.telegram.ui.MaterialGramSettings.isMaterialVoiceEnabled()) {\n"
        "                redDotPaint.setColor(getThemedColor(Theme.key_featuredStickers_addButton));\n"
        "                redDotPaint.setAlpha(255);\n"
        "                org.telegram.ui.MaterialGramVoiceStyle.drawBlob(canvas, getMeasuredWidth() / 2f, getMeasuredHeight() / 2f, dp(11), redDotPaint);\n"
        "                if (!externalFrameClock) {\n"
        "                    invalidate();\n"
        "                }\n"
        "                return;\n"
        "            }\n"
        "            if (playing) {\n"
        "                drawable.setAlpha((int) (255 * alpha));\n"
        "            }\n"
        "            redDotPaint.setAlpha((int) (255 * alpha));\n",
        "the record dot blob"
    )

    # 2) Field for the waveform view.
    enter = replace_once(
        enter,
        "    private RLottieImageView recordDeleteImageView;\n",
        "    private RLottieImageView recordDeleteImageView;\n"
        "    private org.telegram.ui.MaterialGramWaveView materialGramWave;\n",
        "the MaterialGram wave field"
    )

    # 3) The waveform lives in the record panel next to the timer.
    enter = replace_once(
        enter,
        "        recordPanel.addView(recordTimeContainer, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT, Gravity.CENTER_VERTICAL));\n",
        "        recordPanel.addView(recordTimeContainer, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT, Gravity.CENTER_VERTICAL));\n"
        "        if (org.telegram.ui.MaterialGramSettings.isMaterialVoiceEnabled()) {\n"
        "            materialGramWave = new org.telegram.ui.MaterialGramWaveView(getContext());\n"
        "            materialGramWave.setCancelProvider(() -> slideText != null ? slideText.cancelToProgress : 0f);\n"
        "            recordPanel.addView(materialGramWave, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, 28, Gravity.CENTER_VERTICAL));\n"
        "        }\n",
        "the MaterialGram wave view"
    )

    # 4) Feed it with the amplitude Telegram already reports.
    enter = replace_once(
        enter,
        "                recordCircle.setAmplitude((Double) args[1]);\n",
        "                recordCircle.setAmplitude((Double) args[1]);\n"
        "                if (materialGramWave != null) {\n"
        "                    materialGramWave.pushAmplitude(((Double) args[1]).floatValue());\n"
        "                }\n",
        "the MaterialGram wave amplitude feed"
    )

    # 5) The long "slide to cancel" hint makes room for the waveform; the gesture itself is unchanged.
    enter = replace_once(
        enter,
        "            if (cancelToProgress != 1) {\n"
        "                int slideDelta =",
        "            if (cancelToProgress != 1 && !org.telegram.ui.MaterialGramSettings.isMaterialVoiceEnabled()) {\n"
        "                int slideDelta =",
        "the slide to cancel hint"
    )
    write_text(enter_path, enter)
    print("MaterialGram voice recording style was applied.")


def main() -> None:
    if not UPSTREAM.is_dir():
        fail("Telegram submodule is not checked out. Use actions/checkout with submodules: recursive.")

    api_id_raw = os.environ.get("TELEGRAM_API_ID", "").strip()
    api_hash = os.environ.get("TELEGRAM_API_HASH", "").strip()
    if not api_id_raw or not api_hash:
        fail(
            "Telegram API credentials are missing. Add TELEGRAM_API_ID and TELEGRAM_API_HASH "
            "as GitHub Actions repository secrets; do not paste them into source files or chat."
        )
    if not api_id_raw.isdecimal() or int(api_id_raw) <= 0:
        fail("TELEGRAM_API_ID must be a positive integer.")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash):
        fail("TELEGRAM_API_HASH must be a 32-character hexadecimal value.")

    props_path = UPSTREAM / "gradle.properties"
    props = read_text(props_path)
    props = replace_line(props, r"^APP_PACKAGE=.*$", f"APP_PACKAGE={PACKAGE}", "APP_PACKAGE")
    write_text(props_path, props)

    app_gradle_path = UPSTREAM / "TMessagesProj_App" / "build.gradle"
    app_gradle = read_text(app_gradle_path)
    app_gradle, suffix_count = re.subn(
        r'(?m)^\s*applicationIdSuffix\s+"\.beta"\s*\n', "", app_gradle, count=1
    )
    if suffix_count != 1 and 'applicationIdSuffix ".beta"' in app_gradle:
        fail("Could not remove the upstream .beta applicationId suffix safely.")

    stable_keystore = 'storeFile file("../TMessagesProj/config/release.keystore")'
    stable_debug_signer = "signingConfig signingConfigs.debug"
    if stable_keystore not in app_gradle or stable_debug_signer not in app_gradle:
        fail("The pinned Telegram build no longer uses MaterialGram's stable signing configuration.")

    firebase_b64 = os.environ.get("MATERIALGRAM_GOOGLE_SERVICES_JSON_BASE64", "").strip()
    firebase_config_path = UPSTREAM / "TMessagesProj_App" / "google-services.json"
    upstream_firebase_path = UPSTREAM / "TMessagesProj" / "google-services.json"
    if firebase_b64:
        try:
            firebase_raw = base64.b64decode(firebase_b64, validate=True)
            firebase_config = json.loads(firebase_raw.decode("utf-8"))
        except Exception:
            fail("MATERIALGRAM_GOOGLE_SERVICES_JSON_BASE64 is not valid base64-encoded Firebase JSON.")
        packages = {
            client.get("client_info", {}).get("android_client_info", {}).get("package_name")
            for client in firebase_config.get("client", [])
        }
        if PACKAGE not in packages:
            fail("The supplied Firebase config must contain an Android app with package org.materialgram.")
        write_text(firebase_config_path, json.dumps(firebase_config, indent=2) + "\n")
        write_text(upstream_firebase_path, json.dumps(firebase_config, indent=2) + "\n")
    else:
        app_gradle, _ = re.subn(
            r"(?m)^apply plugin: 'com\.google\.gms\.google-services'\s*\n?", "",
            app_gradle
        )
        firebase_config_path.unlink(missing_ok=True)
        upstream_firebase_path.unlink(missing_ok=True)
        print("Firebase config not supplied: the APK will build without Firebase push notifications.")

    write_text(app_gradle_path, app_gradle)

    build_vars_path = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "BuildVars.java"
    build_vars = read_text(build_vars_path)
    build_vars = set_java_value(build_vars, "APP_ID", api_id_raw)
    build_vars = set_java_value(build_vars, "APP_HASH", json.dumps(api_hash))
    build_vars = set_java_value(build_vars, "SAFETYNET_KEY", json.dumps(""))
    build_vars = set_java_value(build_vars, "GOOGLE_AUTH_CLIENT_ID", json.dumps(""))
    build_vars = set_java_value(build_vars, "HUAWEI_APP_ID", json.dumps(""))
    build_vars = set_java_value(build_vars, "HUAWEI_STORE_URL", json.dumps(""))
    build_vars = set_java_value(build_vars, "PLAYSTORE_APP_URL", json.dumps("https://github.com/v0idty/MaterialGram"))
    build_vars = set_java_value(build_vars, "CHECK_UPDATES", "false")
    build_vars = set_java_value(build_vars, "IS_BILLING_UNAVAILABLE", "true")
    build_vars = set_java_value(build_vars, "SUPPORTS_PASSKEYS", "false")
    build_vars = set_java_value(build_vars, "SUPPORTS_FPNV", "false")
    write_text(build_vars_path, build_vars)

    resource_root = UPSTREAM / "TMessagesProj" / "src" / "main" / "res"
    for strings_path in resource_root.glob("values*/strings.xml"):
        strings = read_text(strings_path)
        strings, _ = re.subn(
            r'(<string\s+name="AppName"[^>]*>).*?(</string>)',
            rf"\g<1>MaterialGram\g<2>", strings, count=1
        )
        strings, _ = re.subn(
            r'(<string\s+name="AppNameBeta"[^>]*>).*?(</string>)',
            rf"\g<1>MaterialGram\g<2>", strings, count=1
        )
        write_text(strings_path, strings)

    icon_path = resource_root / "drawable" / "ic_materialgram_icon.xml"
    icon_path.parent.mkdir(parents=True, exist_ok=True)
    icon = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#10B574"
        android:pathData="M0,0H108V108H0Z" />
    <path
        android:fillColor="#F5FFFA"
        android:pathData="M18.4,47.3L84.1,19.6C88.3,17.9 92.1,21.7 90.4,25.9L63.2,89.5C61.4,93.7 55.4,94 53.2,89.9L41.4,68.4L20.2,56.8C16.1,54.6 14.2,49.1 18.4,47.3Z" />
</vector>
"""
    write_text(icon_path, icon)

    manifest_paths = [
        UPSTREAM / "TMessagesProj" / "src" / "main" / "AndroidManifest.xml",
        UPSTREAM / "TMessagesProj" / "config" / "debug" / "AndroidManifest.xml",
        UPSTREAM / "TMessagesProj" / "config" / "debug" / "AndroidManifest_SDK23.xml",
        UPSTREAM / "TMessagesProj" / "config" / "release" / "AndroidManifest.xml",
        UPSTREAM / "TMessagesProj" / "config" / "release" / "AndroidManifest_SDK23.xml",
        UPSTREAM / "TMessagesProj" / "config" / "release" / "AndroidManifest_standalone.xml",
    ]
    for manifest_path in manifest_paths:
        if not manifest_path.is_file():
            continue
        manifest = read_text(manifest_path)
        manifest = manifest.replace(
            'android:icon="@mipmap/ic_launcher"',
            'android:icon="@drawable/ic_materialgram_icon"'
        )
        manifest = manifest.replace(
            'android:roundIcon="@mipmap/ic_launcher_round"',
            'android:roundIcon="@drawable/ic_materialgram_icon"'
        )
        manifest = re.sub(
            r'\s*<meta-data\s+android:name="com\.google\.android\.maps\.v2\.API_KEY"[^>]*/>',
            "", manifest
        )
        write_text(manifest_path, manifest)

    patch_materialgram_features()
    patch_materialgram_avatars()
    patch_materialgram_input()
    patch_materialgram_split_input()
    patch_materialgram_voice()

    print("MaterialGram branding and package ID applied.")
    print("Telegram API credentials injected into the temporary build checkout (values hidden).")
    print("Unofficial-app-only features tied to Telegram's official package have been disabled.")


if __name__ == "__main__":
    main()