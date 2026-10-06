package org.pooltool.android;

import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.opengl.Matrix;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.List;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

final class PoolRenderer implements GLSurfaceView.Renderer {
    private static final float TABLE_HALF_X = 1.2f;
    private static final float TABLE_HALF_Z = 0.65f;
    private static final float BALL_RADIUS = 0.047f;
    private static final float BALL_Y = 0.055f + BALL_RADIUS;
    private static final float MAX_SHOT_SPEED = 3.4f;
    private static final float FIXED_STEP = 1f / 120f;
    private static final float POCKET_RADIUS = 0.072f;

    private final List<Ball> balls = new ArrayList<>();
    private final float[] projection = new float[16];
    private final float[] view = new float[16];
    private final float[] viewProjection = new float[16];
    private final float[] model = new float[16];
    private final float[] mvp = new float[16];

    private int program;
    private int positionAttribute;
    private int normalAttribute;
    private int mvpUniform;
    private int colorUniform;
    private FloatBuffer sphereBuffer;
    private int sphereVertexCount;
    private int surfaceWidth = 1;
    private int surfaceHeight = 1;
    private float aimX;
    private float aimZ = -1f;
    private boolean overheadCamera;
    private long lastFrameNanos;
    private float accumulator;
    private int pocketedCount;

    @Override
    public void onSurfaceCreated(GL10 gl, EGLConfig config) {
        GLES20.glClearColor(0.035f, 0.075f, 0.058f, 1f);
        GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        GLES20.glDepthFunc(GLES20.GL_LEQUAL);
        program = createProgram(VERTEX_SHADER, FRAGMENT_SHADER);
        positionAttribute = GLES20.glGetAttribLocation(program, "aPosition");
        normalAttribute = GLES20.glGetAttribLocation(program, "aNormal");
        mvpUniform = GLES20.glGetUniformLocation(program, "uMvp");
        colorUniform = GLES20.glGetUniformLocation(program, "uColor");
        createSphere();
        resetRack();
    }

    @Override
    public void onSurfaceChanged(GL10 gl, int width, int height) {
        surfaceWidth = Math.max(1, width);
        surfaceHeight = Math.max(1, height);
        GLES20.glViewport(0, 0, surfaceWidth, surfaceHeight);
        float aspect = (float) surfaceWidth / surfaceHeight;
        Matrix.perspectiveM(projection, 0, 42f, aspect, 0.1f, 25f);
    }

    @Override
    public void onDrawFrame(GL10 gl) {
        long now = System.nanoTime();
        if (lastFrameNanos == 0) {
            lastFrameNanos = now;
        }
        float elapsed = Math.min((now - lastFrameNanos) / 1_000_000_000f, 0.05f);
        lastFrameNanos = now;
        accumulator += elapsed;
        while (accumulator >= FIXED_STEP) {
            stepPhysics(FIXED_STEP);
            accumulator -= FIXED_STEP;
        }

        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);
        GLES20.glUseProgram(program);
        configureCamera();
        drawTable();
        drawPockets();
        drawAim();
        drawBalls();
    }

    synchronized void shoot(float screenDx, float screenDy, float distance, int width, int height) {
        Ball cue = cueBall();
        if (cue == null || cue.pocketed || isMoving()) {
            return;
        }

        float dx = screenDx / Math.max(1, width);
        float dz = screenDy / Math.max(1, height);
        float magnitude = (float) Math.hypot(dx, dz);
        if (magnitude < 0.0001f) {
            return;
        }
        aimX = dx / magnitude;
        aimZ = dz / magnitude;

        float power = Math.min(1f, distance / Math.max(1f, Math.min(width, height) * 0.55f));
        float speed = 0.35f + power * MAX_SHOT_SPEED;
        cue.vx = aimX * speed;
        cue.vz = aimZ * speed;
    }

    synchronized void resetRack() {
        balls.clear();
        pocketedCount = 0;
        balls.add(new Ball(0, 0.055f + BALL_RADIUS, 0.37f, 0xFFF6F1E7, true));

        int[] colors = {
                0xFFF4D03F, 0xFF3585D5, 0xFFD74343, 0xFF8746B5, 0xFFF18B35,
                0xFF2A9C60, 0xFF8B3232, 0xFF2B2B32, 0xFFF4D03F, 0xFF3585D5,
                0xFFD74343, 0xFF8746B5, 0xFFF18B35, 0xFF2A9C60, 0xFF8B3232
        };
        int ballIndex = 0;
        float rackZ = -0.16f;
        float spacing = BALL_RADIUS * 2.08f;
        for (int row = 0; row < 5; row++) {
            for (int col = 0; col <= row; col++) {
                float x = (col - row * 0.5f) * spacing;
                float z = rackZ - row * spacing * 0.88f;
                balls.add(new Ball(x, BALL_Y, z, colors[ballIndex++], false));
            }
        }
        aimX = 0f;
        aimZ = -1f;
    }

    synchronized void toggleCamera() {
        overheadCamera = !overheadCamera;
    }

    private void configureCamera() {
        float eyeY = overheadCamera ? 4.4f : 2.55f;
        float eyeZ = overheadCamera ? 0.02f : 2.85f;
        Matrix.setLookAtM(view, 0, 0f, eyeY, eyeZ, 0f, 0f, 0f, 0f, 1f, 0f);
        Matrix.multiplyMM(viewProjection, 0, projection, 0, view, 0);
    }

    private void drawTable() {
        drawBox(0f, -0.015f, 0f, 2.62f, 0.18f, 1.42f, color(0xFF442B1D));
        drawBox(0f, 0.055f, 0f, 2.4f, 0.035f, 1.3f, color(0xFF16744B));

        float railY = 0.12f;
        float railHeight = 0.13f;
        float railWidth = 0.11f;
        drawBox(0f, railY, -0.65f, 2.62f, railHeight, railWidth, color(0xFF573923));
        drawBox(0f, railY, 0.65f, 2.62f, railHeight, railWidth, color(0xFF573923));
        drawBox(-1.2f, railY, 0f, railWidth, railHeight, 1.3f, color(0xFF573923));
        drawBox(1.2f, railY, 0f, railWidth, railHeight, 1.3f, color(0xFF573923));
        drawBox(0f, 0.073f, -0.54f, 2.18f, 0.025f, 0.025f, color(0xFF4DC080));
    }

    private void drawPockets() {
        float[][] positions = {
                {-1.12f, -0.57f}, {0f, -0.59f}, {1.12f, -0.57f},
                {-1.12f, 0.57f}, {0f, 0.59f}, {1.12f, 0.57f}
        };
        for (float[] position : positions) {
            drawDisk(position[0], 0.077f, position[1], 0.075f, color(0xFF101313));
        }
    }

    private synchronized void drawBalls() {
        for (Ball ball : balls) {
            if (ball.pocketed) {
                continue;
            }
            Matrix.setIdentityM(model, 0);
            Matrix.translateM(model, 0, ball.x, BALL_Y, ball.z);
            Matrix.scaleM(model, 0, BALL_RADIUS, BALL_RADIUS, BALL_RADIUS);
            setMvp(model);
            GLES20.glUniform4fv(colorUniform, 1, color(ball.color), 0);
            GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0);
            sphereBuffer.position(0);
            GLES20.glEnableVertexAttribArray(positionAttribute);
            GLES20.glVertexAttribPointer(positionAttribute, 3, GLES20.GL_FLOAT, false, 24, sphereBuffer);
            sphereBuffer.position(3);
            GLES20.glEnableVertexAttribArray(normalAttribute);
            GLES20.glVertexAttribPointer(normalAttribute, 3, GLES20.GL_FLOAT, false, 24, sphereBuffer);
            GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, sphereVertexCount);
        }
    }

    private synchronized void drawAim() {
        Ball cue = cueBall();
        if (cue == null || cue.pocketed || isMoving()) {
            return;
        }
        float lineStartX = cue.x + aimX * BALL_RADIUS * 1.4f;
        float lineStartZ = cue.z + aimZ * BALL_RADIUS * 1.4f;
        drawLine(lineStartX, BALL_Y, lineStartZ,
                lineStartX + aimX * 0.9f, BALL_Y, lineStartZ + aimZ * 0.9f,
                color(0xAAE9F1D2), 2.5f);
        drawLine(cue.x - aimX * 0.16f, BALL_Y, cue.z - aimZ * 0.16f,
                cue.x - aimX * 0.48f, BALL_Y + 0.012f, cue.z - aimZ * 0.48f,
                color(0xFFB87945), 8f);
    }

    private void drawBox(float x, float y, float z, float width, float height, float depth, float[] rgba) {
        float[] vertices = boxVertices(width, height, depth);
        Matrix.setIdentityM(model, 0);
        Matrix.translateM(model, 0, x, y, z);
        setMvp(model);
        drawTriangles(vertices, rgba);
    }

    private void drawDisk(float x, float y, float z, float radius, float[] rgba) {
        float[] vertices = new float[32 * 3 * 6];
        int offset = 0;
        for (int i = 0; i < 32; i++) {
            float a = (float) (i * Math.PI * 2 / 32);
            float b = (float) ((i + 1) * Math.PI * 2 / 32);
            offset = putVertex(vertices, offset, x, y, z);
            offset = putVertex(vertices, offset, x + (float) Math.cos(a) * radius, y, z + (float) Math.sin(a) * radius);
            offset = putVertex(vertices, offset, x + (float) Math.cos(b) * radius, y, z + (float) Math.sin(b) * radius);
        }
        Matrix.setIdentityM(model, 0);
        setMvp(model);
        drawTriangles(vertices, rgba);
    }

    private void drawLine(float x1, float y1, float z1, float x2, float y2, float z2, float[] rgba, float width) {
        float[] vertices = {x1, y1, z1, 0f, 1f, 0f, x2, y2, z2, 0f, 1f, 0f};
        Matrix.setIdentityM(model, 0);
        setMvp(model);
        GLES20.glLineWidth(width);
        drawLines(vertices, rgba);
    }

    private void drawTriangles(float[] vertices, float[] rgba) {
        FloatBuffer buffer = floatBuffer(vertices);
        GLES20.glUniform4fv(colorUniform, 1, rgba, 0);
        GLES20.glEnableVertexAttribArray(positionAttribute);
        GLES20.glEnableVertexAttribArray(normalAttribute);
        buffer.position(0);
        GLES20.glVertexAttribPointer(positionAttribute, 3, GLES20.GL_FLOAT, false, 24, buffer);
        buffer.position(3);
        GLES20.glVertexAttribPointer(normalAttribute, 3, GLES20.GL_FLOAT, false, 24, buffer);
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, vertices.length / 6);
    }

    private void drawLines(float[] vertices, float[] rgba) {
        FloatBuffer buffer = floatBuffer(vertices);
        GLES20.glUniform4fv(colorUniform, 1, rgba, 0);
        GLES20.glEnableVertexAttribArray(positionAttribute);
        GLES20.glEnableVertexAttribArray(normalAttribute);
        buffer.position(0);
        GLES20.glVertexAttribPointer(positionAttribute, 3, GLES20.GL_FLOAT, false, 24, buffer);
        buffer.position(3);
        GLES20.glVertexAttribPointer(normalAttribute, 3, GLES20.GL_FLOAT, false, 24, buffer);
        GLES20.glDrawArrays(GLES20.GL_LINES, 0, vertices.length / 6);
    }

    private void setMvp(float[] transform) {
        Matrix.multiplyMM(mvp, 0, viewProjection, 0, transform, 0);
        GLES20.glUniformMatrix4fv(mvpUniform, 1, false, mvp, 0);
    }

    private void stepPhysics(float dt) {
        synchronized (this) {
            for (Ball ball : balls) {
                if (ball.pocketed) {
                    continue;
                }
                ball.x += ball.vx * dt;
                ball.z += ball.vz * dt;
                float speed = (float) Math.hypot(ball.vx, ball.vz);
                if (speed > 0f) {
                    float newSpeed = Math.max(0f, speed - 0.42f * dt);
                    float scale = newSpeed / speed;
                    ball.vx *= scale;
                    ball.vz *= scale;
                    if (newSpeed < 0.015f) {
                        ball.vx = 0f;
                        ball.vz = 0f;
                    }
                }
                pocketIfReached(ball);
                if (!ball.pocketed) {
                    collideWithCushions(ball);
                }
            }

            for (int i = 0; i < balls.size(); i++) {
                Ball first = balls.get(i);
                if (first.pocketed) {
                    continue;
                }
                for (int j = i + 1; j < balls.size(); j++) {
                    Ball second = balls.get(j);
                    if (!second.pocketed) {
                        collide(first, second);
                    }
                }
            }
        }
    }

    private void pocketIfReached(Ball ball) {
        float[][] pockets = {
                {-1.12f, -0.57f}, {0f, -0.59f}, {1.12f, -0.57f},
                {-1.12f, 0.57f}, {0f, 0.59f}, {1.12f, 0.57f}
        };
        for (float[] pocket : pockets) {
            if (Math.hypot(ball.x - pocket[0], ball.z - pocket[1]) < POCKET_RADIUS) {
                ball.pocketed = true;
                ball.vx = 0f;
                ball.vz = 0f;
                pocketedCount++;
                if (ball.cue) {
                    ball.pocketed = false;
                    ball.x = 0f;
                    ball.z = 0.37f;
                }
                return;
            }
        }
    }

    private void collideWithCushions(Ball ball) {
        float limitX = TABLE_HALF_X - BALL_RADIUS * 1.5f;
        float limitZ = TABLE_HALF_Z - BALL_RADIUS * 1.5f;
        if (Math.abs(ball.x) > limitX && Math.abs(ball.z) > 0.46f) {
            ball.x = Math.copySign(limitX, ball.x);
            ball.vx *= -0.82f;
        }
        if (Math.abs(ball.z) > limitZ && Math.abs(ball.x) > 0.92f) {
            ball.z = Math.copySign(limitZ, ball.z);
            ball.vz *= -0.82f;
        }
        if (ball.x < -1.075f || ball.x > 1.075f) {
            ball.x = Math.max(-1.075f, Math.min(1.075f, ball.x));
            ball.vx *= -0.88f;
        }
        if (ball.z < -0.52f || ball.z > 0.52f) {
            ball.z = Math.max(-0.52f, Math.min(0.52f, ball.z));
            ball.vz *= -0.88f;
        }
    }

    private void collide(Ball first, Ball second) {
        float dx = second.x - first.x;
        float dz = second.z - first.z;
        float distanceSquared = dx * dx + dz * dz;
        float diameter = BALL_RADIUS * 2f;
        if (distanceSquared >= diameter * diameter || distanceSquared < 0.000001f) {
            return;
        }

        float distance = (float) Math.sqrt(distanceSquared);
        float nx = dx / distance;
        float nz = dz / distance;
        float overlap = (diameter - distance) * 0.5f;
        first.x -= nx * overlap;
        first.z -= nz * overlap;
        second.x += nx * overlap;
        second.z += nz * overlap;

        float relativeVelocity = (second.vx - first.vx) * nx + (second.vz - first.vz) * nz;
        if (relativeVelocity >= 0f) {
            return;
        }
        float impulse = -(1f + 0.96f) * relativeVelocity * 0.5f;
        first.vx -= impulse * nx;
        first.vz -= impulse * nz;
        second.vx += impulse * nx;
        second.vz += impulse * nz;
    }

    private boolean isMoving() {
        for (Ball ball : balls) {
            if (!ball.pocketed && Math.hypot(ball.vx, ball.vz) > 0.015f) {
                return true;
            }
        }
        return false;
    }

    private Ball cueBall() {
        for (Ball ball : balls) {
            if (ball.cue) {
                return ball;
            }
        }
        return null;
    }

    private void createSphere() {
        int latitudeBands = 14;
        int longitudeBands = 20;
        float[] vertices = new float[latitudeBands * longitudeBands * 6 * 6];
        int offset = 0;
        for (int lat = 0; lat < latitudeBands; lat++) {
            float lat0 = (float) (Math.PI * (-0.5 + (double) lat / latitudeBands));
            float lat1 = (float) (Math.PI * (-0.5 + (double) (lat + 1) / latitudeBands));
            for (int lon = 0; lon < longitudeBands; lon++) {
                float lon0 = (float) (Math.PI * 2 * lon / longitudeBands);
                float lon1 = (float) (Math.PI * 2 * (lon + 1) / longitudeBands);
                float[] a = spherePoint(lat0, lon0);
                float[] b = spherePoint(lat1, lon0);
                float[] c = spherePoint(lat1, lon1);
                float[] d = spherePoint(lat0, lon1);
                offset = putVertex(vertices, offset, a);
                offset = putVertex(vertices, offset, b);
                offset = putVertex(vertices, offset, c);
                offset = putVertex(vertices, offset, a);
                offset = putVertex(vertices, offset, c);
                offset = putVertex(vertices, offset, d);
            }
        }
        sphereBuffer = floatBuffer(vertices);
        sphereVertexCount = vertices.length / 6;
    }

    private static float[] spherePoint(float latitude, float longitude) {
        float y = (float) Math.sin(latitude);
        float ring = (float) Math.cos(latitude);
        float x = ring * (float) Math.cos(longitude);
        float z = ring * (float) Math.sin(longitude);
        return new float[] {x, y, z, x, y, z};
    }

    private static int putVertex(float[] buffer, int offset, float x, float y, float z) {
        buffer[offset++] = x;
        buffer[offset++] = y;
        buffer[offset++] = z;
        buffer[offset++] = 0f;
        buffer[offset++] = 1f;
        buffer[offset++] = 0f;
        return offset;
    }

    private static int putVertex(float[] buffer, int offset, float[] vertex) {
        System.arraycopy(vertex, 0, buffer, offset, vertex.length);
        return offset + vertex.length;
    }

    private static float[] boxVertices(float width, float height, float depth) {
        float x = width * 0.5f;
        float y = height * 0.5f;
        float z = depth * 0.5f;
        float[] vertices = new float[36 * 6];
        int offset = 0;
        offset = face(vertices, offset, new float[] {-x, -y, z}, new float[] {x, -y, z},
                new float[] {x, y, z}, new float[] {-x, y, z}, 0f, 0f, 1f);
        offset = face(vertices, offset, new float[] {x, -y, -z}, new float[] {-x, -y, -z},
                new float[] {-x, y, -z}, new float[] {x, y, -z}, 0f, 0f, -1f);
        offset = face(vertices, offset, new float[] {-x, y, z}, new float[] {x, y, z},
                new float[] {x, y, -z}, new float[] {-x, y, -z}, 0f, 1f, 0f);
        offset = face(vertices, offset, new float[] {-x, -y, -z}, new float[] {x, -y, -z},
                new float[] {x, -y, z}, new float[] {-x, -y, z}, 0f, -1f, 0f);
        offset = face(vertices, offset, new float[] {x, -y, z}, new float[] {x, -y, -z},
                new float[] {x, y, -z}, new float[] {x, y, z}, 1f, 0f, 0f);
        face(vertices, offset, new float[] {-x, -y, -z}, new float[] {-x, -y, z},
                new float[] {-x, y, z}, new float[] {-x, y, -z}, -1f, 0f, 0f);
        return vertices;
    }

    private static int face(float[] vertices, int offset, float[] a, float[] b, float[] c,
            float[] d, float nx, float ny, float nz) {
        offset = appendFaceVertex(vertices, offset, a, nx, ny, nz);
        offset = appendFaceVertex(vertices, offset, b, nx, ny, nz);
        offset = appendFaceVertex(vertices, offset, c, nx, ny, nz);
        offset = appendFaceVertex(vertices, offset, a, nx, ny, nz);
        offset = appendFaceVertex(vertices, offset, c, nx, ny, nz);
        return appendFaceVertex(vertices, offset, d, nx, ny, nz);
    }

    private static int appendFaceVertex(float[] vertices, int offset, float[] p,
            float nx, float ny, float nz) {
        vertices[offset++] = p[0];
        vertices[offset++] = p[1];
        vertices[offset++] = p[2];
        vertices[offset++] = nx;
        vertices[offset++] = ny;
        vertices[offset++] = nz;
        return offset;
    }

    private static FloatBuffer floatBuffer(float[] values) {
        FloatBuffer buffer = ByteBuffer.allocateDirect(values.length * 4)
                .order(ByteOrder.nativeOrder())
                .asFloatBuffer();
        buffer.put(values);
        buffer.position(0);
        return buffer;
    }

    private static float[] color(int argb) {
        return new float[] {
                ((argb >> 16) & 0xFF) / 255f,
                ((argb >> 8) & 0xFF) / 255f,
                (argb & 0xFF) / 255f,
                ((argb >> 24) & 0xFF) / 255f
        };
    }

    private static int createProgram(String vertexShader, String fragmentShader) {
        int vertex = compileShader(GLES20.GL_VERTEX_SHADER, vertexShader);
        int fragment = compileShader(GLES20.GL_FRAGMENT_SHADER, fragmentShader);
        int shaderProgram = GLES20.glCreateProgram();
        GLES20.glAttachShader(shaderProgram, vertex);
        GLES20.glAttachShader(shaderProgram, fragment);
        GLES20.glLinkProgram(shaderProgram);
        int[] status = new int[1];
        GLES20.glGetProgramiv(shaderProgram, GLES20.GL_LINK_STATUS, status, 0);
        if (status[0] == 0) {
            String log = GLES20.glGetProgramInfoLog(shaderProgram);
            GLES20.glDeleteProgram(shaderProgram);
            throw new IllegalStateException("Could not link pool renderer: " + log);
        }
        GLES20.glDeleteShader(vertex);
        GLES20.glDeleteShader(fragment);
        return shaderProgram;
    }

    private static int compileShader(int type, String source) {
        int shader = GLES20.glCreateShader(type);
        GLES20.glShaderSource(shader, source);
        GLES20.glCompileShader(shader);
        int[] status = new int[1];
        GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, status, 0);
        if (status[0] == 0) {
            String log = GLES20.glGetShaderInfoLog(shader);
            GLES20.glDeleteShader(shader);
            throw new IllegalStateException("Could not compile pool renderer shader: " + log);
        }
        return shader;
    }

    private static final String VERTEX_SHADER =
            "attribute vec3 aPosition;\n" +
            "attribute vec3 aNormal;\n" +
            "uniform mat4 uMvp;\n" +
            "varying float vLight;\n" +
            "void main() {\n" +
            "  vec3 light = normalize(vec3(-0.4, 0.8, 0.5));\n" +
            "  vLight = 0.50 + 0.50 * max(dot(normalize(aNormal), light), 0.0);\n" +
            "  gl_Position = uMvp * vec4(aPosition, 1.0);\n" +
            "}\n";

    private static final String FRAGMENT_SHADER =
            "precision mediump float;\n" +
            "uniform vec4 uColor;\n" +
            "varying float vLight;\n" +
            "void main() {\n" +
            "  gl_FragColor = vec4(uColor.rgb * vLight, uColor.a);\n" +
            "}\n";

    private static final class Ball {
        final int color;
        final boolean cue;
        float x;
        float y;
        float z;
        float vx;
        float vz;
        boolean pocketed;

        Ball(float x, float y, float z, int color, boolean cue) {
            this.x = x;
            this.y = y;
            this.z = z;
            this.color = color;
            this.cue = cue;
        }
    }
}
