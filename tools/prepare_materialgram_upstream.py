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
    """Patch the pinned Telegram UI with MaterialGram's optional adaptive navigation."""
    ui_root = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui"
    messenger_root = UPSTREAM / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger"

    # Persist the user preference separately from Telegram's own settings.
    settings_helper = ui_root / "MaterialGramSettings.java"
    write_text(settings_helper, """package org.telegram.ui;

import android.content.Context;
import org.telegram.messenger.ApplicationLoader;

/** Preferences owned by the MaterialGram fork. */
public final class MaterialGramSettings {
    private static final String PREFERENCES = "materialgram_settings";
    private static final String KEY_BOTTOM_NAVIGATION = "bottom_navigation_enabled";

    private MaterialGramSettings() {
    }

    public static boolean isBottomNavigationEnabled() {
        final Context context = ApplicationLoader.applicationContext;
        return context == null || context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
                .getBoolean(KEY_BOTTOM_NAVIGATION, true);
    }

    public static void setBottomNavigationEnabled(boolean enabled) {
        final Context context = ApplicationLoader.applicationContext;
        if (context != null) {
            context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
                    .edit()
                    .putBoolean(KEY_BOTTOM_NAVIGATION, enabled)
                    .apply();
        }
    }
}
""")

    # A dedicated MaterialGram settings page with a real persistent switch.
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
    private static final int ROW_HEADER = 0;
    private static final int ROW_NAVIGATION = 1;
    private static final int ROW_INFO = 2;

    private RecyclerListView listView;
    private ListAdapter adapter;

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
        if (position != ROW_NAVIGATION) {
            return;
        }
        MaterialGramSettings.setBottomNavigationEnabled(!MaterialGramSettings.isBottomNavigationEnabled());
        adapter.notifyItemChanged(ROW_NAVIGATION);
        updateMainTabs();
    }

    private void updateMainTabs() {
        final INavigationLayout layout = getParentLayout();
        if (layout == null) {
            return;
        }
        for (BaseFragment fragment : layout.getFragmentStack()) {
            if (fragment instanceof MainTabsActivity) {
                ((MainTabsActivity) fragment).updateMaterialGramNavigation();
            }
        }
    }

    private class ListAdapter extends RecyclerListView.SelectionAdapter {
        private final Context context;

        private ListAdapter(Context context) {
            this.context = context;
        }

        @Override
        public int getItemCount() {
            return 3;
        }

        @Override
        public boolean isEnabled(RecyclerView.ViewHolder holder) {
            return holder.getAdapterPosition() == ROW_NAVIGATION;
        }

        @NonNull
        @Override
        public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view;
            if (viewType == ROW_HEADER) {
                view = new HeaderCell(context);
            } else if (viewType == ROW_NAVIGATION) {
                view = new TextCheckCell(context);
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
            if (position == ROW_HEADER) {
                ((HeaderCell) holder.itemView).setText(
                        LocaleController.getString(R.string.MaterialGramNavigationHeader)
                );
            } else if (position == ROW_NAVIGATION) {
                ((TextCheckCell) holder.itemView).setTextAndCheck(
                        LocaleController.getString(R.string.MaterialGramNavigationEnabled),
                        MaterialGramSettings.isBottomNavigationEnabled(),
                        false
                );
            } else {
                ((TextInfoPrivacyCell) holder.itemView).setText(
                        LocaleController.getString(R.string.MaterialGramNavigationInfo)
                );
            }
        }

        @Override
        public int getItemViewType(int position) {
            return position;
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

    # Add MaterialGram's settings entry at the top of Telegram's Settings list.
    controller_path = ui_root / "MainTabsActivityController.java"
    write_text(controller_path, """package org.telegram.ui;

public interface MainTabsActivityController {
    void setTabsVisible(boolean visible);
    void setTabsScrollCollapsed(boolean collapsed);
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

    # Telegram already implements the expanding selected capsule. Extend its
    # native MainTabsActivity with a separate search button and the opt-in gate.
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
    main_tabs = replace_once(
        main_tabs,
        "    public void selectTab(int position, boolean animated) {\n"
        "        for (int a = 0; a < tabs.length; a++) {\n",
        "    public void selectTab(int position, boolean animated) {\n"
        "        animatorTabsScrollCollapsed.setValue(false, animated);\n"
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
        "            if (getUserConfig().showCallsTab) {\n"
        "                Bundle args = new Bundle();\n"
        "                args.putBoolean(\"needFinishFragment\", false);\n"
        "                args.putBoolean(\"hasMainTabs\", true);\n"
        "                return new CallLogActivity(args);\n"
        "            }\n",
        "            if (getUserConfig().showCallsTab && !MaterialGramSettings.isBottomNavigationEnabled()) {\n"
        "                Bundle args = new Bundle();\n"
        "                args.putBoolean(\"needFinishFragment\", false);\n"
        "                args.putBoolean(\"hasMainTabs\", true);\n"
        "                return new CallLogActivity(args);\n"
        "            }\n",
        "the Settings tab selection for MaterialGram navigation"
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
    main_tabs = replace_once(
        main_tabs,
        "        float alpha = (1f - isProfile * hide) * animatorTabsVisible.getFloatValue();\n",
        "        float alpha = MaterialGramSettings.isBottomNavigationEnabled() ? (1f - isProfile * hide) * animatorTabsVisible.getFloatValue() : 0f;\n",
        "the optional navigation fade"
    )
    main_tabs = replace_once(
        main_tabs,
        "        final float factor = animatorTabsVisible.getFloatValue();\n",
        "        final float factor = MaterialGramSettings.isBottomNavigationEnabled() ? animatorTabsVisible.getFloatValue() : 0f;\n",
        "the optional navigation visibility factor"
    )
    main_tabs = replace_once(
        main_tabs,
        "        final float factor = MaterialGramSettings.isBottomNavigationEnabled() ? animatorTabsVisible.getFloatValue() : 0f;\n"
        "        final float scale = lerp(0.85f, 1f, factor);\n"
        "\n"
        "        tabsViewWrapper.setTranslationY(lerp(hiddenY, normalY, factor));\n"
        "        tabsView.setClickable(factor > 1);\n"
        "        tabsView.setEnabled(factor > 1);\n"
        "        tabsView.setAlpha(factor);\n"
        "        tabsView.setVisibility(factor > 0 ? View.VISIBLE : View.GONE);\n",
        "        final float factor = MaterialGramSettings.isBottomNavigationEnabled() ? animatorTabsVisible.getFloatValue() : 0f;\n"
        "        final float collapsed = animatorTabsScrollCollapsed.getFloatValue();\n"
        "\n"
        "        tabsViewWrapper.setTranslationY(lerp(hiddenY, normalY, factor) + dp(15) * collapsed);\n"
        "        tabsView.setClickable(factor > 0.5f);\n"
        "        tabsView.setEnabled(factor > 0.5f);\n"
        "        tabsView.setAlpha(factor * lerp(1f, 0.88f, collapsed));\n"
        "        tabsView.setVisibility(factor > 0 ? View.VISIBLE : View.GONE);\n",
        "the recoverable compact tab layout"
    )
    main_tabs = replace_once(
        main_tabs,
        "        tabsView.setVisibility(factor > 0 ? View.VISIBLE : View.GONE);\n",
        "        tabsView.setVisibility(factor > 0 ? View.VISIBLE : View.GONE);\n"
        "        tabsViewWrapper.setVisibility(factor > 0 ? View.VISIBLE : View.GONE);\n",
        "the navigation wrapper visibility"
    )
    main_tabs = replace_once(
        main_tabs,
        "            tabsView.setViewVisible(tabs[INDEX_SETTINGS], !callTabsVisible, animated);\n"
        "            tabsView.setViewVisible(tabs[INDEX_CALLS], callTabsVisible, animated);\n",
        "            final boolean showCalls = callTabsVisible && !MaterialGramSettings.isBottomNavigationEnabled();\n"
        "            tabsView.setViewVisible(tabs[INDEX_SETTINGS], !showCalls, animated);\n"
        "            tabsView.setViewVisible(tabs[INDEX_CALLS], showCalls, animated);\n",
        "the MaterialGram Settings tab visibility"
    )
    main_tabs = replace_once(
        main_tabs,
        "    private class MainTabsActivityControllerImpl implements MainTabsActivityController {\n",
        "    public void updateMaterialGramNavigation() {\n"
        "        if (tabsView == null || tabsViewWrapper == null) {\n"
        "            return;\n"
        "        }\n"
        "        final boolean enabled = MaterialGramSettings.isBottomNavigationEnabled();\n"
        "        animatorTabsVisible.setValue(enabled, true);\n"
        "        animatorTabsScrollCollapsed.setValue(false, false);\n"
        "        checkUi_callTabVisible(getUserConfig().showCallsTab, false);\n"
        "        if (enabled && dialogsActivity != null) {\n"
        "            dialogsActivity.resetMaterialGramTabsScrollVisibility();\n"
        "        }\n"
        "        checkUi_tabsPosition();\n"
        "        checkUi_fadeView();\n"
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
        "            }\n"
        "        }\n"
        "    }\n",
        "the independent scroll-collapse controller method"
    )
    write_text(main_tabs_path, main_tabs)

    # Make the native chat-list scroll listener hide/reveal the capsule by direction.
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
        "                    if (dy != 0 && mainTabsActivityController != null && viewPages != null && viewPages.length > 0 && recyclerView == viewPages[0].listView && viewPage.dialogsType == DIALOGS_TYPE_DEFAULT && !searching) {\n"
        "                        mainTabsActivityController.setTabsScrollCollapsed(dy > 0);\n"
        "                    }\n",
        "the chat-list scroll direction handler"
    )
    dialogs = replace_once(
        dialogs,
        "        final boolean mainTabsVisible = !searching && (blurredView == null || blurredView.getBackground() == null || blurredView.getAlpha() < 0.01f || blurredView.getVisibility() == View.GONE);\n",
        "        final boolean mainTabsVisible = !searching && (blurredView == null || blurredView.getBackground() == null || blurredView.getAlpha() < 0.01f || blurredView.getVisibility() == View.GONE);\n",
        "the chat-list driven tab visibility condition"
    )
    write_text(dialogs_path, dialogs)

    # Add Russian base resources; localized resource folders fall back to values/.
    strings_path = UPSTREAM / "TMessagesProj" / "src" / "main" / "res" / "values" / "strings.xml"
    strings = read_text(strings_path)
    additions = [
        ('MaterialGramSettings', 'Настройки MaterialGram'),
        ('MaterialGramSettingsInfo', 'Дополнительные настройки интерфейса MaterialGram'),
        ('MaterialGramNavigationHeader', 'Нижняя панель навигации'),
        ('MaterialGramNavigationEnabled', 'Включить панель MaterialGram'),
        ('MaterialGramNavigationInfo', 'Плавающая панель с активной капсулой. При прокрутке чатов вниз она компактно смещается, оставаясь доступной; при прокрутке вверх возвращается.'),
    ]
    for name, value in additions:
        if f'name="{name}"' not in strings:
            entry = f'    <string name="{name}">{value}</string>\n'
            strings = replace_once(strings, "</resources>", entry + "</resources>", f"the {name} string resource")
    write_text(strings_path, strings)

    print("MaterialGram adaptive navigation and its settings screen were applied.")


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

    # Keep the same signer for every MaterialGram APK so updates install in place.
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

    print("MaterialGram branding and package ID applied.")
    print("Telegram API credentials injected into the temporary build checkout (values hidden).")
    print("Unofficial-app-only features tied to Telegram's official package have been disabled.")


if __name__ == "__main__":
    main()
