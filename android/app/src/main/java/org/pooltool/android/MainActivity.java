package org.pooltool.android;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

public final class MainActivity extends Activity {
    private PoolSurface surface;
    private PoolRenderer renderer;
    private float touchX;
    private float touchY;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        renderer = new PoolRenderer();
        surface = new PoolSurface(this, renderer);

        FrameLayout root = new FrameLayout(this);
        root.addView(surface, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        TextView instructions = new TextView(this);
        instructions.setText(R.string.instructions);
        instructions.setTextColor(Color.WHITE);
        instructions.setTextSize(15);
        instructions.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        instructions.setBackgroundColor(0xAA10251E);
        instructions.setPadding(20, 12, 20, 12);
        FrameLayout.LayoutParams instructionParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.TOP | Gravity.CENTER_HORIZONTAL);
        instructionParams.topMargin = 18;
        root.addView(instructions, instructionParams);

        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        controls.setGravity(Gravity.CENTER);
        controls.setPadding(8, 8, 8, 8);
        controls.setBackgroundColor(0xAA10251E);

        TextView rackButton = makeButton(R.string.new_rack);
        rackButton.setOnClickListener(view -> renderer.resetRack());
        controls.addView(rackButton);

        TextView cameraButton = makeButton(R.string.camera);
        cameraButton.setOnClickListener(view -> renderer.toggleCamera());
        LinearLayout.LayoutParams cameraParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        cameraParams.leftMargin = 8;
        controls.addView(cameraButton, cameraParams);

        FrameLayout.LayoutParams controlParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        controlParams.bottomMargin = 18;
        root.addView(controls, controlParams);

        surface.setOnTouchListener(this::handleTouch);
        setContentView(root);
    }

    private TextView makeButton(int label) {
        TextView button = new TextView(this);
        button.setText(label);
        button.setTextColor(Color.WHITE);
        button.setTextSize(15);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setGravity(Gravity.CENTER);
        button.setPadding(20, 12, 20, 12);
        button.setBackgroundColor(0xFF287A53);
        button.setClickable(true);
        return button;
    }

    private boolean handleTouch(View view, MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                touchX = event.getX();
                touchY = event.getY();
                return true;
            case MotionEvent.ACTION_UP:
                float dx = event.getX() - touchX;
                float dy = event.getY() - touchY;
                float distance = (float) Math.hypot(dx, dy);
                if (distance > 24) {
                    renderer.shoot(dx, dy, distance, view.getWidth(), view.getHeight());
                } else {
                    view.performClick();
                }
                return true;
            case MotionEvent.ACTION_CANCEL:
                return true;
            default:
                return true;
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (surface != null) {
            surface.onResume();
        }
    }

    @Override
    protected void onPause() {
        if (surface != null) {
            surface.onPause();
        }
        super.onPause();
    }

    private static final class PoolSurface extends GLSurfaceView {
        PoolSurface(Activity activity, PoolRenderer renderer) {
            super(activity);
            setEGLContextClientVersion(2);
            setRenderer(renderer);
            setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);
            setFocusable(true);
        }

        @Override
        public boolean performClick() {
            super.performClick();
            return true;
        }
    }
}
